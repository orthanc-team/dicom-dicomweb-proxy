FROM orthancteam/orthanc-pre-release:python-cmove2-unstable
#TODO: replace with right Orthanc

COPY proxy.py /scripts/

ENV ORTHANC__PYTHON_SCRIPT="/scripts/proxy.py"
ENV DICOM_WEB_PLUGIN_ENABLED="true"