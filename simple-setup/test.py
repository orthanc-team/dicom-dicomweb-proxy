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

    @classmethod
    def setUpClass(cls):
        subprocess.run(["docker", "compose", "down", "-v"], cwd=here)
        subprocess.run(["docker", "compose", "up", "--build", "-d"], cwd=here)

        cls.oa = OrthancApiClient('http://localhost:8042', user='demo', pwd='demo')
        cls.oa.wait_started()
        cls.ob = OrthancApiClient('http://localhost:8043', user='demo', pwd='demo')
        cls.ob.wait_started()
        cls.oc = OrthancApiClient('http://localhost:8044', user='demo', pwd='demo')
        cls.oc.wait_started()

    @classmethod
    def tearDownClass(cls):
        pass
        # subprocess.run(["docker", "compose", "down", "-v"], cwd=here)


    def test_c_find(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()
        self.oc.delete_all_content()

        # let's fill the orthanc C (Pacs)
        self.oc.upload_file("../stimuli/CT_small.dcm")

        remote_studies = self.oa.modalities.query_studies(
            from_modality="proxy",
            query={
                'PatientID': '1C*',
                'StudyDescription': ''
            }
        )

        self.assertEqual(1, len(remote_studies))
        self.assertEqual('1.3.6.1.4.1.5962.1.2.1.20040119072730.12322', remote_studies[0].dicom_id)
        self.assertEqual("e+1", remote_studies[0].tags.get('StudyDescription'))

    def test_c_move(self):
        self.oa.delete_all_content()
        self.ob.delete_all_content()
        self.oc.delete_all_content()

        # let's fill the orthanc C (Pacs)
        self.oc.upload_folder(here / "../stimuli/Brainix")

        self.oa.modalities.retrieve_study(
            from_modality="proxy",
            dicom_id="2.16.840.1.113669.632.20.1211.10000357775"
        )

        self.assertEqual(1, len(self.oa.studies.get_all_ids()))
        self.assertEqual(3, len(self.oa.instances.get_all_ids()))

        # let's verify that the proxy is cleared after the transfer
        self.assertEqual(0, len(self.ob.instances.get_all_ids()))

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    unittest.main()

