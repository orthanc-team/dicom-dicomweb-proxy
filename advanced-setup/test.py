import time
import unittest
import subprocess

from orthanc_api_client import OrthancApiClient
import pathlib
import logging

here = pathlib.Path(__file__).parent.resolve()

logger = logging.getLogger('dicom-dicomweb-proxy')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class TestProxy(unittest.TestCase):
    '''
    This allows to test the proxy when the credentials used by the proxy have permissions only on some labels.
    prerequisites:
    - manually start the setup (docker compose up -d --build)
    - create a client secret in Keycloak (through the UI of KC) and put it in the compose (and then restart the setup)
    - create an api-key for the 'admin' user: '9876543210'
    - create an api-key for the 'doctor' user: '0123456789'
    - run the test: `python3 test.py`
    '''

    @classmethod
    def setUpClass(cls):
        # subprocess.run(["docker", "compose", "down", "-v"], cwd=here)
        # subprocess.run(["docker", "compose", "up", "--build", "-d"], cwd=here)

        cls.oa = OrthancApiClient('http://localhost:8042', user='demo', pwd='demo')
        cls.oa.wait_started()
        cls.ob = OrthancApiClient('http://localhost:8043', user='demo', pwd='demo')
        cls.ob.wait_started()
        cls.oc_admin = OrthancApiClient('http://localhost/orthanc/', headers={"api-key": "9876543210"})
        cls.oc_admin.wait_started()

    @classmethod
    def tearDownClass(cls):
        #subprocess.run(["docker", "compose", "down", "-v"], cwd=here)
        pass


    def test_c_find(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()
        self.oc_admin.delete_all_content()

        # let's fill the orthanc C (Pacs)
        instances_ids = self.oc_admin.upload_file("../stimuli/CT_small.dcm")
        self.oc_admin.upload_file("../stimuli/CT_small2.dcm")
        study_id = self.oc_admin.instances.get_parent_study_id(instances_ids[0])

        # let's apply a label on the study 1
        self.oc_admin.studies.add_label(study_id, "test")

        remote_studies = self.oa.modalities.query_studies(
            from_modality="proxy",
            query={
                'PatientID': '*',
                'StudyDescription': ''
            }
        )

        # only one study should be found, the one with the label
        self.assertEqual(1, len(remote_studies))
        self.assertEqual('1.3.6.1.4.1.5962.1.2.1.20040119072730.12322', remote_studies[0].dicom_id)
        self.assertEqual("e+1", remote_studies[0].tags.get('StudyDescription'))

    def test_c_move(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()
        self.oc_admin.delete_all_content()

        # let's fill the orthanc C (Pacs)
        instances_ids = self.oc_admin.upload_file("../stimuli/CT_small.dcm")
        self.oc_admin.upload_file("../stimuli/CT_small2.dcm")
        study_id = self.oc_admin.instances.get_parent_study_id(instances_ids[0])

        # let's apply a label on the study 1
        self.oc_admin.studies.add_label(study_id, "test")

        # the study one (labeled) should be retrieved
        self.oa.modalities.retrieve_study(
            from_modality="proxy",
            dicom_id="1.3.6.1.4.1.5962.1.2.1.20040119072730.12322"
        )

        self.assertEqual(1, len(self.oa.studies.get_all_ids()))

        # the study 2 (not labeled) should not be retrieved!
        with self.assertRaises(Exception):
            self.oa.modalities.retrieve_study(
                from_modality="proxy",
                dicom_id="1.2.276.0.7230010.3.1.2.1717646434.1.1707928889.331715"
            )


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    unittest.main()

