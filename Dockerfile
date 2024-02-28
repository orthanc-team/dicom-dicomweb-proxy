FROM orthancteam/orthanc-pre-release:python-cmove2-unstable

COPY proxy.py /scripts/

ENV ORTHANC__PYTHON_SCRIPT="/scripts/proxy.py"
ENV DICOM_WEB_PLUGIN_ENABLED="true"