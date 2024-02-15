# Purpose

This is a sample setup to demonstrate how an Orthanc instance can be used to serve as a dicom-to-dicomweb proxy
between a DICOM compliant modality and a dicomweb compliant PACS.

This advanced setup includes Keycloak.
The Orthanc user has permissions only on a specific tag, so that not all the studies are available.

# Description

This demo contains the same containers as the sample setup plus:
- Keycloak (+ kc db)
- auth service
- permissions file

# Starting the setup

- To start the setup, type: `docker-compose up --build`
- visit Keycloak admin page, get the client secret and put it in the compose, the restart the setup
- still in Keycloak admin page, add an `api-key` attribute (and value) for the user from the proxy 

# demo
TODO