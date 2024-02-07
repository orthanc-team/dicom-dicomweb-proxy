FROM orthancteam/orthanc:24.2.0

COPY proxy.py /scripts/

ENV ORTHANC__PYTHON_SCRIPT="/scripts/proxy.py"
ENV DICOM_WEB_PLUGIN_ENABLED="true"