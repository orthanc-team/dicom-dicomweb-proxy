# Purpose

This is a sample setup to demonstrate how an Orthanc instance can be used to serve as a dicom-to-dicomweb proxy
between a DICOM compliant modality and a dicomweb compliant PACS.

This advanced setup includes Keycloak and is based on the [orthanc-auth-service](https://github.com/orthanc-team/orthanc-auth-service/tree/main/minimal-setup/keycloak) demo setup.
The Orthanc user has permissions only on a specific tag, so that not all the studies are available.
Of course, this setup is relevant only if the DICOMweb server to query is Orthanc...

# Description

This demo contains the same containers as the sample setup plus:
- Keycloak (+ kc db)
- auth service
- permissions file

# Starting the setup

- To start the setup, type: `docker-compose up -d --build`
- visit [Keycloak admin page](http://localhost/keycloak/admin/master/console/), get the client secret and put it in the compose, then restart the setup
- still in Keycloak admin page, add an `api-key` attribute (and value) for the user from the proxy 
