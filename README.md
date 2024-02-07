# DICOM-DICOMweb-Proxy

This Orthanc includes a plugin and acts as a dicom-to-dicomweb proxy between a DICOM compliant modality and a DICOMweb compliant PACS.

## How it works?

This plugin allows to convert:
- a C-find query (DICOM protocol) to a QidoRs query (DICOMweb protocol)
- a C-move query (DICOM protocol) to a WadoRs query (DICOMweb protocol)

As soon as a C-find is received from a DICOM node, Orthanc will query the DICOMweb server with the filters received in the C-find.
Then, Orthanc will convert the answer from the DICOMweb server and send a DICOM answer to the initial DICOM node.

In the same way, as soon as a C-Move is received, Orthanc will get the resources from the DICOMweb server.
Then, Orthanc will push (C-Move) these resources to the initial DICOM node. 

IMPORTANT notes:
- The QueryRetrieveLevel 'PATIENT' is not supported by this plugin.
- For C-find queries, the 'called AET' has to be identical to the alias of the DICOMweb server you want to query
- For C-move queries, the 'source AET' has to be identical to the alias of the DICOMweb server you want to query


## How to use it ?
- Configure Orthanc as usually (through env var or via json)
- In your Orthanc configuration, add the DICOM node you want to make exchanging with the DICOMweb server
- In your Orthanc configuration, add the DICOMweb server (and the credentials) you want to make answering to the DICOM node
- Configure your DICOM node so that the `called AET` is identical to the alias of the DICOMweb server in the Orthanc configuration (needed for C-find)
- Configure your DICOM node so that the `source AET` is identical to the alias of the DICOMweb server in the Orthanc configuration (needed for C-move)
