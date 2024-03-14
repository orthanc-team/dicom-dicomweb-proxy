import json
import time

import orthanc
import pprint
from typing import List
import dataclasses

'''
This plugin allows to convert:
- a C-find query (DICOM protocol) to a QidoRs query (DICOMweb protocol)
- a C-move query (DICOM protocol) to a WadoRs query (DICOMweb protocol)

As soon as a C-find is received from a DICOM node, Orthanc will query the DICOMweb server
with the filters received in the C-find.
Then, Orthanc will convert the answer from the DICOMweb server and send a DICOM answer to the initial DICOM node.

In the same way, as soon as a C-Move is received, Orthanc will get the resources from the DICOMweb server.
Then, Orthanc will push (C-Move) these resources to the initial DICOM node. 

IMPORTANT notes:
- The QueryRetrieveLevel 'PATIENT' is not supported by this plugin.
- For C-find queries, the 'called AET' has to be identical to the alias of the DICOMweb server you want to query
- For C-move queries, the 'source AET' has to be identical to the alias of the DICOMweb server you want to query


'''
def GetMimeNameFromCharSet(charSet: str):
    '''
    Allows to get a valid 'Accept-Charset'  value for the dicomweb query, based on the DICOM tag 'SpecificCharacterSet'
    from: https://dicom.nema.org/medical/dicom/current/output/html/part18.html#table_D-1
    '''
    CHARSET_MAPPING = {
        'ISO_IR 100': 'ISO-8859-1',
        'ISO_IR 101': 'ISO-8859-2',
        'ISO_IR 109': 'ISO-8859-3',
        'ISO_IR 110': 'ISO-8859-4',
        'ISO_IR 144': 'ISO-8859-5',
        'ISO_IR 127': 'ISO-8859-6',
        'ISO_IR 126': 'ISO-8859-7',
        'ISO_IR 138': 'ISO-8859-8',
        'ISO_IR 148': 'ISO-8859-9',
        'ISO_IR 203': 'ISO-8859-15',
        'ISO_IR 166': 'TIS-620',
        'ISO 2022 IR 13': 'ISO-2022-JP',
        'ISO 2022 IR 87': 'ISO-2022-JP',
        'ISO 2022 IR 6': 'ISO-2022-KR',
        'ISO 2022 IR 149': 'ISO-2022-KR',
        'ISO 2022 IR 6': 'ISO-2022-CN',
        'ISO 2022 IR 58': 'ISO-2022-CN',
        'GB18030': 'GB18030',
        'GBK': 'GBK',
        'ISO_IR 192': 'UTF-8'
    }
    return CHARSET_MAPPING.get(charSet, "UTF-8")

def GetLevel(dicomLevel: str):
    LEVEL_MAPPING = {
        'IMAGE': 'instances',
        'SERIES': 'series',
        'STUDY': 'studies'
    }
    # defaulting to 'studies', patient level is not supported
    return LEVEL_MAPPING.get(dicomLevel, "studies")

def QidoRs(query, dicomwebServerAlias = None):
    '''
    Builds a Qido RS query from the DICOM query received;
    Queries the dicomweb server;
    Returns the result (dict)
    '''

    # let's build the query
    arguments = {}
    acceptCharset = "UTF-8"
    for i in range(query.GetFindQuerySize()):
        # The QueryRetrieveLevel (0008,0052) is not needed in the Qido Args, but in the Uri
        if query.GetFindQueryTagName(i) == "QueryRetrieveLevel":
            level = GetLevel(query.GetFindQueryValue(i))
        elif query.GetFindQueryTagName(i) == "SpecificCharacterSet":
            acceptCharset = GetMimeNameFromCharSet(query.GetFindQueryValue(i))
        else:
            tag = query.GetFindQueryTagName(i)
            arguments[tag] = query.GetFindQueryValue(i)

    payloadDict = {
        "Uri": level,
        "HttpHeaders": {
            "Accept": "application/dicom",
            "Accept-Charset": acceptCharset
        },
        "Arguments": arguments
    }

    # let's send the query and return the result
    r = orthanc.RestApiPostAfterPlugins('/dicom-web/servers/{0}/get'.format(dicomwebServerAlias), json.dumps(payloadDict))

    return json.loads(r)

def BuildTagsListFromDicomWebAnswer(answer):
    '''
    Builds a tags list as it is expected by the DICOM protocol.
    We have to go from that:
    {
        "00080020" :
        {
            "Value" : [ "20130812" ],
            "vr" : "DA"
        }
    }
    to something like that:
    {
        "00080020" : "20130812"
    }
    :param answer: a dict, as returned by a dicomweb server
    :return: a dict, as expected by a dicom server
    '''

    dicomDict = {}
    for tag, value_info in answer.items():
        # some tags don't have any value...
        if "Value" in value_info:
            value = value_info["Value"][0]
            # some tags contain a dict...
            if isinstance(value, dict):
                # If the value is a dictionary, extract the appropriate field
                if "Alphabetic" in value:
                    dicomDict[tag] = value["Alphabetic"]
                else:
                    raise Exception('The tag {0} does contain this dict: {1}, but this dict is not expected in the proxy plugin!'.format(tag, value))
            # most of the tags simply contain a value:
            else:
                dicomDict[tag] = str(value)

    return dicomDict

def OnFind(answers, query, issuerAet, calledAet):
    dicomWebAnswer = QidoRs(query=query, dicomwebServerAlias=calledAet)

    for answer in dicomWebAnswer:
        dicomTagsList = BuildTagsListFromDicomWebAnswer(answer)

        answers.FindAddAnswer(orthanc.CreateDicom(
            json.dumps(dicomTagsList), None, orthanc.CreateDicomFlags.NONE))


def GetOrthancAliasFromAET(AET):
    '''
    The initial DICOM query will contain an AET, but we need the Orthanc alias to perform the C-Store
    :param AET: AET to send the resource to
    :return: the Orthanc alias corresponding to the AET
    '''
    modalities = json.loads(orthanc.RestApiGet('/modalities?expand'))

    for modality, modalityDetails in modalities.items():
        if modalityDetails["AET"] == AET:
            return modality

    raise Exception('It seems that the modality issuing the original DICOM query is not registered in the Proxy config!')




@dataclasses.dataclass
class RemoteInstance:
    study_instance_uid: str
    series_instance_uid: str
    sop_instance_uid: str

class MoveDriver:

    def __del__(self):
        print("+++++++++++MoveDriver being deallocated")

    def __init__(self, request) -> None:
        self.request = request
        self.remote_instances = []
        self.local_instances_ids = []
        self.instance_counter = 0
        self.memory = [0] * 10000000

        if request["SourceAET"] in {None, ''}:
            raise Exception('The DICOM query does not contain a value for the SourceAET, unable to process it!')

        if request["Level"] in {None, ''}:
            raise Exception('The DICOM query does not contain a value for the tag Level, unable to process it!')

        self.level = request["Level"]
        self.remote_server = request["SourceAET"]

        if request["StudyInstanceUID"] in {None, ''}:
            raise Exception('The DICOM query does not contain a value for the StudyInstanceUID, unable to process it!')
        else:
            self.study_instance_uid = request["StudyInstanceUID"]

        if self.level in {"SERIES", "IMAGE"}:
            if request["SeriesInstanceUID"] in {None, ''}:
                raise Exception('The DICOM query does not contain a value for the SeriesInstanceUID, unable to process it!')
            else:
                self.series_instance_uid = request["SeriesInstanceUID"]

            if self.level == "IMAGE":

                if request["SOPInstanceUID"] in {None, ''}:
                    raise Exception('The DICOM query does not contain a value for the SOPInstanceUID, unable to process it!')
                else:
                    sop_instance_uid = request["SOPInstanceUID"]
                    self.remote_instances = [
                        RemoteInstance(study_instance_uid=self.study_instance_uid,
                                    series_instance_uid=self.series_instance_uid,
                                    sop_instance_uid=sop_instance_uid)
                    ]

        self.target_aet = None
        if request["TargetAET"] in {None, ''}:
            self.target_aet = request["OriginatorAET"]
        else:
            self.target_aet = request["TargetAET"]

        self.target_modality_alias = GetOrthancAliasFromAET(self.target_aet)


    # get the url where each instance can be downloaded
    def get_instances_list(self):
        request = self.request

        # Let's build the payload
        
        if self.level == "STUDY":
            url = f"studies/{self.study_instance_uid}/metadata"
        elif self.level == "SERIES":
            url = f"studies/{self.study_instance_uid}/series/{self.series_instance_uid}/metadata"

        payloadDict = {
            "Uri": url,
            "HttpHeaders": {
                "Accept": "application/json"
            }
        }

        # let's send the query and return the result
        dw_instances = json.loads(orthanc.RestApiPostAfterPlugins('/dicom-web/servers/{0}/get'.format(self.remote_server), json.dumps(payloadDict)))
        # pprint.pprint(dw_instances)
        self.remote_instances = []
        for dw_instance in dw_instances:
            if '00080018' in dw_instance and '0020000E' in dw_instance and '0020000D' in dw_instance:
                self.remote_instances.append(RemoteInstance(study_instance_uid=dw_instance['0020000D']['Value'][0],
                                                            series_instance_uid=dw_instance['0020000E']['Value'][0],
                                                            sop_instance_uid=dw_instance['00080018']['Value'][0]))

    def retrieve_next_instance(self) -> str:
        # retrieve one instance from the DICOMWeb server
        if self.instance_counter > len(self.remote_instances):
            raise Exception('Trying to retrieve an instance that has not been listed!')

        remote_instance = self.remote_instances[self.instance_counter]
        self.instance_counter += 1

        resources = {}
        resources["Study"] = remote_instance.study_instance_uid
        resources["Series"] = remote_instance.series_instance_uid
        resources["Instance"] = remote_instance.sop_instance_uid

        payloadDict = {
            "Resources": [resources]
        }

        r = orthanc.RestApiPostAfterPlugins('/dicom-web/servers/{0}/retrieve'.format(self.remote_server), json.dumps(payloadDict))

        orthanc_id = orthanc.LookupInstance(remote_instance.sop_instance_uid)
        self.local_instances_ids.append(orthanc_id)
        
        return orthanc_id
        
    def forward_instance(self, orthanc_id: str):
        # C-store from proxy to issuer
        orthanc.RestApiPost('/modalities/{0}/store'.format(self.target_modality_alias), json.dumps({
            "Resources": [orthanc_id]
        }))

    def cleanup(self):
        orthanc.RestApiPost('/tools/bulk-delete', json.dumps({
            "Resources": self.local_instances_ids
        }))


def CreateMoveCallback(**request):
    # simply create the move driver object now and return it to Orthanc
    orthanc.LogInfo("CreateMoveCallback")
    # pprint.pprint(request)

    driver = MoveDriver(request=request)

    return driver

def GetMoveSizeCallback(driver: MoveDriver):
    # query the remote server to list and count the instances to retrieve
    orthanc.LogInfo("GetMoveSizeCallback")

    driver.get_instances_list()

    return len(driver.remote_instances)

def ApplyMoveCallback(driver: MoveDriver):
    # move one instance at a time from the DICOMWeb server to the target via the proxy
    orthanc.LogInfo("ApplyMoveCallback")

    instance_id = driver.retrieve_next_instance()
    driver.forward_instance(instance_id)

    return 0 # 0 is success, you should raise an exception in case of errors

def FreeMoveCallback(driver):
    # free the resources that have been allocated by the move driver
    orthanc.LogInfo("FreeMoveCallback")

    driver.cleanup()
    

orthanc.RegisterFindCallback(OnFind)
orthanc.RegisterMoveCallback2(CreateMoveCallback, GetMoveSizeCallback, ApplyMoveCallback, FreeMoveCallback)