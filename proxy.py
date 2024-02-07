import json
import time

import orthanc

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

# todo: test scenario

def WadoRs(request, dicomwebServerAlias = None):

    # Let's build the payload
    if request["Level"] in {None, ''}:
        raise Exception('The DICOM query does not contain a value for the tag Level, unable to process it!')
    else:
        level = request["Level"]

    resources = {}

    if request["StudyInstanceUID"] in {None, ''}:
        raise Exception('The DICOM query does not contain a value for the StudyInstanceUID, unable to process it!')
    else:
        resources["Study"] = request["StudyInstanceUID"]

    if level in {"SERIES", "IMAGE"}:
        if request["SeriesInstanceUID"] in {None, ''}:
            raise Exception('The DICOM query does not contain a value for the SeriesInstanceUID, unable to process it!')
        else:
            resources["Series"] = request["SeriesInstanceUID"]
        if level == "IMAGE":
            if request["SOPInstanceUID"] in {None, ''}:
                raise Exception('The DICOM query does not contain a value for the SOPInstanceUID, unable to process it!')
            else:
                resources["Instance"] = request["SOPInstanceUID"]

    payloadDict = {
        "Resources": [resources]
    }

    # let's send the query
    r = orthanc.RestApiPostAfterPlugins('/dicom-web/servers/{0}/retrieve'.format(dicomwebServerAlias), json.dumps(payloadDict))

    if len(json.loads(r)) == 2:
        if level == "SERIES":
            orthancId = orthanc.LookupSeries(request["SeriesInstanceUID"])
        elif level == "IMAGE":
            orthancId = orthanc.LookupInstance(request["SOPInstanceUID"])
        else:
            orthancId = orthanc.LookupStudy(request["StudyInstanceUID"])
        return orthancId
    else:
        raise Exception('The DICOMweb query was not successful!')

def GetOrthancAliasFromAET(AET):
    '''
    The initial DICOM query will contain an AET, but we need the Orthanc alias to perform the C-Store
    :param AET: AET to send the resource to
    :return: the Orthanc alias corresponding to the AET
    '''
    modalities = json.loads(orthanc.RestApiGet('/modalities'))

    for modality in modalities:
        modalityDetails = json.loads(orthanc.RestApiGet('/modalities/{0}/configuration'.format(modality)))
        if modalityDetails["AET"] == AET:
            return modality

    raise Exception('It seems that the modality issuing the original DICOM query is not registered in the Proxy config!')

def OnMove(**request):
    print("entering in move------------------")
    time.sleep(18)
    # fetch the resource from the dicomweb server
    if request["SourceAET"] in {None, ''}:
        raise Exception('The DICOM query does not contain a value for the SourceAET, unable to process it!')
    else:
        dicomwebServerAlias = request["SourceAET"]

    orthancId = WadoRs(request=request, dicomwebServerAlias=dicomwebServerAlias)

    target = None
    if request["TargetAET"] in {None, ''}:
        target = request["OriginatorAET"]
    else:
        target = request["TargetAET"]

    modalityAlias = GetOrthancAliasFromAET(target)

    # C-store from proxy to issuer
    orthanc.RestApiPost('/modalities/{0}/store'.format(modalityAlias), orthancId)


    # Delete resource from the proxy
    if request["Level"] == "PATIENT":
        raise Exception('Patient level not supported by the proxy!')
    elif request["Level"] == "STUDY":
        orthanc.RestApiDelete('/studies/{0}'.format(orthancId))
    elif request["Level"] == "SERIES":
        orthanc.RestApiDelete('/series/{0}'.format(orthancId))
    elif request["Level"] == "IMAGE":
        orthanc.RestApiDelete('/instances/{0}'.format(orthancId))


orthanc.RegisterFindCallback(OnFind)
orthanc.RegisterMoveCallback(OnMove)