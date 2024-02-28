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

To start the setup, type: `docker-compose up -d --build`

# demo

- login/pwd = demo/demo
- Connect to the orthanc simulating the dicomweb pacs on [http://localhost:8044/ui/app/](http://localhost:8044/ui/app/) (demo/demo).
- Upload an image to this instance of Orthanc.
- Open the orthanc simulating the dicom modality on [http://localhost:8042/ui/app/](http://localhost:8042/ui/app/) (demo/demo).
- In OE2, open the `DICOM Modalities` menu and select `proxy`.
- Click the search button, you should see the content of the `orthanc-pacs` that has been retrieved via the Proxy (C-Find to QIDO-RS conversion).
- If you click on `Retrieve`, the study shall be retrieved via the proxy (C-Move to WADO-RS conversion)