# Purpose

This is a sample setup to demonstrate how an Orthanc instance can be used to serve as a dicom-to-dicomweb proxy
between a DICOM compliant modality and a dicomweb compliant PACS.

# Description

This demo contains:

- an Orthanc-modality container that simulates a DICOM compliant modality (but not dicomweb compliant).
- an Orthanc-pacs container that simulates a dicomweb compliant PACS.
- an Orthanc-proxy container that serves as a 'proxy' between the modality and the PACS to convert dicom queries from
the modality to dicomweb queries. It also converts the dicomweb replies from the pacs to dicom replies.


# Starting the setup

To start the setup, type: `docker-compose up --build`

# demo

- login/pwd = demo/demo
- Connect to the orthanc simulating the dicomweb pacs on [http://localhost:8044](http://localhost:8044).
- Upload an image to this instance of Orthanc.
- Open the orthanc simulating the dicom modality on [http://localhost:8042](http://localhost:8042).
- Query the dicomweb node to get the study you uploaded and try to get it 