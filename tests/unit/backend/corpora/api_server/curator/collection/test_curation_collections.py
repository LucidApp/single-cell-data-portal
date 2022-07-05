import json
import unittest
from unittest.mock import patch, Mock

from backend.corpora.common.corpora_orm import (
    CollectionVisibility,
    ProcessingStatus,
    DatasetArtifactFileType,
    DbDataset,
)
from tests.unit.backend.corpora.api_server.base_api_test import BaseAuthAPITest
from tests.unit.backend.corpora.api_server.mock_auth import make_token
from tests.unit.backend.fixtures.config import fake_s3_file


class TestAuthToken(BaseAuthAPITest):
    @patch("backend.corpora.lambdas.api.v1.curation.collections.collection_uuid.dataset.sts_client")
    def test__generate_s3_credentials__OK(self, sts_client: Mock):
        def _test(user_name: str, additional_scope: list = None):
            token_claims = dict(sub=user_name, email="fake_user@email.com")
            token = make_token(token_claims, additional_scope=additional_scope, token_duration=10)
            sts_client.assume_role_with_web_identity = Mock(
                return_value={
                    "Credentials": {
                        "AccessKeyId": "test_key",
                        "SecretAccessKey": "test_session_token",
                        "SessionToken": "test_session_token",
                    }
                }
            )
            collection = self.generate_collection(self.session)
            headers = {"Authorization": f"Bearer {token}"}

            response = self.app.post(
                f"/curation/v1/collections/{collection.id}/datasets/s3-upload-credentials", headers=headers
            )
            self.assertEqual(200, response.status_code)
            self.assertEqual(response.json["Bucket"], "cellxgene-dataset-submissions-test")
            self.assertEqual(response.json["UploadKeyPrefix"], f"{user_name}/{collection.id}/")
            self.assertEqual(response.json["UploadKeyPrefix"], f"{user_name}/{collection.id}/")

        with self.subTest("collection owner"):
            _test(
                user_name="test_user_id",
            )

        with self.subTest("super curator"):
            _test(
                user_name="test_super_user_id",
                additional_scope="write:collections",
            )

    def test__generate_s3_credentials__Not_Owner(self):
        collection = self.generate_collection(self.session, owner="not_test_user")
        response = self.app.post(
            f"/curation/v1/collections/{collection.id}/datasets/s3-upload-credentials", headers=self.get_auth_headers()
        )
        self.assertEqual(403, response.status_code, msg=response.data)

    def test__generate_s3_credentials__Not_Private(self):
        collection = self.generate_collection(self.session, visibility=CollectionVisibility.PUBLIC.name)
        response = self.app.post(
            f"/curation/v1/collections/{collection.id}/datasets/s3-upload-credentials", headers=self.get_auth_headers()
        )
        self.assertEqual(403, response.status_code)

    def test__generate_s3_credentials__No_Auth(self):
        collection = self.generate_collection(self.session, visibility=CollectionVisibility.PUBLIC.name)
        response = self.app.post(f"/curation/v1/collections/{collection.id}/datasets/s3-upload-credentials")
        self.assertEqual(401, response.status_code)


class TestPostCollection(BaseAuthAPITest):
    def setUp(self):
        super().setUp()
        self.test_collection = dict(
            name="collection", description="description", contact_name="john doe", contact_email="johndoe@email.com"
        )

    def test__create_collection__no_auth(self):
        response = self.app.post("/curation/v1/collections", data=json.dumps(self.test_collection))
        self.assertEqual(401, response.status_code)

    def test__create_collection__OK(self):
        response = self.app.post(
            "/curation/v1/collections", headers=self.get_auth_headers(), data=json.dumps(self.test_collection)
        )
        self.assertEqual(201, response.status_code)

    def test__create_collection__InvalidParameters(self):
        tests = [
            (
                dict(
                    name="",
                    description="",
                    contact_name="",
                    contact_email="@email.com",
                    links=[{"link_type": "DOI", "link_url": "bad_doi"}],
                ),
                [
                    {"name": "contact_email", "reason": "Invalid format."},
                    {"name": "description", "reason": "Cannot be blank."},
                    {"name": "name", "reason": "Cannot be blank."},
                    {"name": "contact_name", "reason": "Cannot be blank."},
                    {"link_type": "DOI", "reason": "Invalid DOI"},
                ],
            ),
            (
                dict(
                    name="not blank",
                    description="description",
                    contact_name="some name",
                    contact_email="robot@email.com",
                    links=[
                        {"link_type": "DOI", "link_url": "doi:duplicated"},
                        {"link_type": "DOI", "link_url": "doi:duplicated"},
                    ],
                ),
                [{"link_type": "DOI", "reason": "Can only specify a single DOI"}],
            ),
        ]
        for body, expected_errors in tests:
            with self.subTest(body):
                response = self.app.post(
                    "/curation/v1/collections", headers=self.get_auth_headers(), data=json.dumps(body)
                )
                self.assertEqual(400, response.status_code)
                for error in expected_errors:
                    self.assertIn(error, response.json["detail"])


class TestGetCollections(BaseAuthAPITest):
    def setUp(self):
        super().setUp()
        self.test_collection = dict(
            name="collection", description="description", contact_name="john doe", contact_email="johndoe@email.com"
        )

    def test__get_collections_no_auth__OK(self):
        res_no_auth = self.app.get("/curation/v1/collections")
        self.assertEqual(200, res_no_auth.status_code)
        self.assertEqual(6, len(res_no_auth.json["collections"]))
        [self.assertEqual("PUBLIC", c["visibility"]) for c in res_no_auth.json["collections"]]

    def test__get_collections_with_auth__OK(self):
        res_auth = self.app.get("/curation/v1/collections", headers=self.get_auth_headers())
        self.assertEqual(200, res_auth.status_code)
        self.assertEqual(6, len(res_auth.json["collections"]))

    def test__get_collections_no_auth_visibility_private__OK(self):
        params = {"visibility": "PRIVATE"}
        res_private = self.app.get("/curation/v1/collections", query_string=params)
        self.assertEqual(401, res_private.status_code)

    def test__get_collections_no_auth_visibility_public__OK(self):
        params = {"visibility": "PUBLIC"}
        res_public = self.app.get("/curation/v1/collections", query_string=params)
        self.assertEqual(200, res_public.status_code)
        self.assertEqual(6, len(res_public.json["collections"]))

    def test__get_only_public_collections_with_auth__OK(self):
        params = {"visibility": "PUBLIC"}
        res = self.app.get("/curation/v1/collections", query_string=params, headers=self.get_auth_headers())
        self.assertEqual(200, res.status_code)
        self.assertEqual(6, len(res.json["collections"]))
        [self.assertEqual("PUBLIC", c["visibility"]) for c in res.json["collections"]]

    def test__get_only_private_collections_with_auth__OK(self):
        second_collection = self.generate_collection(self.session)
        for status in (ProcessingStatus.PENDING, ProcessingStatus.SUCCESS):
            self.generate_dataset(
                self.session,
                collection_id=second_collection.id,
                processing_status={"processing_status": status},
            ).id
        params = {"visibility": "PRIVATE"}
        res = self.app.get("/curation/v1/collections", query_string=params, headers=self.get_auth_headers())
        with self.subTest("Summary collection-level processing statuses are accurate"):
            for collection in res.json["collections"]:
                if collection["id"] == second_collection.id:
                    self.assertEqual(collection["processing_status"], "PENDING")
                else:
                    self.assertEqual(collection["processing_status"], "SUCCESS")
        self.assertEqual(200, res.status_code)
        self.assertEqual(2, len(res.json["collections"]))
        [self.assertEqual("PRIVATE", c["visibility"]) for c in res.json["collections"]]


class TestGetCollectionUUID(BaseAuthAPITest):
    expected_body = {
        "collection_url": "http://frontend.corporanet.local:3000/collections/test_collection_id",
        "contact_email": "somebody@chanzuckerberg.com",
        "contact_name": "Some Body",
        "curator_name": "",
        "datasets": [
            {
                "assay": [{"label": "test_assay", "ontology_term_id": "test_obo"}],
                "cell_count": None,
                "cell_type": [{"label": "test_cell_type", "ontology_term_id": "test_opo"}],
                "curator_tag": None,
                "dataset_assets": [{"filename": "test_filename", "filetype": "H5AD"}],
                "development_stage": [{"label": "test_development_stage", "ontology_term_id": "test_obo"}],
                "disease": [
                    {"label": "test_disease", "ontology_term_id": "test_obo"},
                    {"label": "test_disease2", "ontology_term_id": "test_obp"},
                    {"label": "test_disease3", "ontology_term_id": "test_obq"},
                ],
                "ethnicity": [{"label": "test_ethnicity", "ontology_term_id": "test_obo"}],
                "explorer_url": "test_url",
                "id": "test_dataset_id",
                "is_primary_data": "PRIMARY",
                "mean_genes_per_cell": 0.0,
                "name": "test_dataset_name",
                "organism": [{"label": "test_organism", "ontology_term_id": "test_obo"}],
                "processing_status": "PENDING",
                "revised_at": None,
                "revision": 0,
                "schema_version": "2.0.0",
                "sex": [
                    {"label": "test_sex", "ontology_term_id": "test_obo"},
                    {"label": "test_sex2", "ontology_term_id": "test_obp"},
                ],
                "tissue": [{"label": "test_tissue", "ontology_term_id": "test_obo"}],
                "tombstone": False,
                "x_approximate_distribution": "NORMAL",
                "x_normalization": "test_x_normalization",
            }
        ],
        "description": "test_description",
        "id": "test_collection_id",
        "links": [
            {"link_name": "test_doi_link_name", "link_type": "DOI", "link_url": "http://test_doi_url.place"},
            {"link_name": None, "link_type": "DOI", "link_url": "http://test_no_link_name_doi_url.place"},
            {
                "link_name": "test_raw_data_link_name",
                "link_type": "RAW_DATA",
                "link_url": "http://test_raw_data_url.place",
            },
            {"link_name": None, "link_type": "RAW_DATA", "link_url": "http://test_no_link_name_raw_data_url.place"},
            {
                "link_name": "test_protocol_link_name",
                "link_type": "PROTOCOL",
                "link_url": "http://test_protocol_url.place",
            },
            {"link_name": None, "link_type": "PROTOCOL", "link_url": "http://test_no_link_name_protocol_url.place"},
            {
                "link_name": "test_lab_website_link_name",
                "link_type": "LAB_WEBSITE",
                "link_url": "http://test_lab_website_url.place",
            },
            {
                "link_name": None,
                "link_type": "LAB_WEBSITE",
                "link_url": "http://test_no_link_name_lab_website_url.place",
            },
            {"link_name": "test_other_link_name", "link_type": "OTHER", "link_url": "http://test_other_url.place"},
            {"link_name": None, "link_type": "OTHER", "link_url": "http://test_no_link_name_other_url.place"},
            {
                "link_name": "test_data_source_link_name",
                "link_type": "DATA_SOURCE",
                "link_url": "http://test_data_source_url.place",
            },
            {
                "link_name": None,
                "link_type": "DATA_SOURCE",
                "link_url": "http://test_no_link_name_data_source_url.place",
            },
        ],
        "name": "test_collection_name",
        "published_at": None,
        "publisher_metadata": None,
        "revised_at": None,
        "revision_of": None,
        "tombstone": False,
        "visibility": "PUBLIC",
    }

    def setUp(self):
        super().setUp()
        self.test_collection = dict(
            name="collection", description="description", contact_name="john doe", contact_email="johndoe@email.com"
        )

    def test__get_public_collection_verify_body_is_reshaped_correctly__OK(self):
        dataset = self.session.query(DbDataset).filter(DbDataset.id == "test_dataset_id").one_or_none()
        self.assertIsInstance(dataset.organism, list)
        # Make this entry a dict instead of a list to test ability of the handler to reshape to list/array
        dataset.organism = dataset.organism[0]
        self.session.flush()
        dataset_modified = self.session.query(DbDataset).filter(DbDataset.id == "test_dataset_id").one_or_none()
        self.assertIsInstance(dataset_modified.organism, dict)

        res = self.app.get("/curation/v1/collections/test_collection_id")
        self.assertEqual(200, res.status_code)
        res_body = res.json
        del res_body["created_at"]  # too finicky; ignore
        self.assertTrue("access_type" not in res_body)
        self.assertDictEqual(self.expected_body, res_body)  # Confirm dict has been packaged in list

    def test__get_private_collection__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_revision")
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id_revision", res.json["id"])
        self.assertTrue("access_type" not in res.json)

    def test__get_nonexistent_collection__Not_Found(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_nonexistent")
        self.assertEqual(404, res.status_code)

    def test__get_public_collection_with_auth_access_type_write__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id", headers=self.get_auth_headers())
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id", res.json["id"])
        self.assertEqual("WRITE", res.json["access_type"])

    def test__get_public_collection_with_auth_access_type_read__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_not_owner", headers=self.get_auth_headers())
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id_not_owner", res.json["id"])
        self.assertEqual("READ", res.json["access_type"])

    def test__get_private_collection_with_auth_access_type_write__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_revision", headers=self.get_auth_headers())
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id_revision", res.json["id"])
        self.assertEqual("WRITE", res.json["access_type"])


class TestPutCollectionUUID(BaseAuthAPITest):
    def setUp(self):
        super().setUp()
        self.test_collection = dict(
            name="collection", description="description", contact_name="john doe", contact_email="johndoe@email.com"
        )
        self.generate_collection(
            self.session,
            id="test_curator_tag_collection_id",
            visibility=CollectionVisibility.PUBLIC.name,
            owner="test_user_id",
            name="test_collection_name",
            description="test_description",
            data_submission_policy_version="0",
            contact_name="Some Body",
            contact_email="somebody@chanzuckerberg.com",
        )
        self.generate_dataset(
            self.session,
            id="test_curator_tag",
            curator_tag="curator_tag",
            revision=0,
            name="test_dataset_name",
            schema_version="2.0.0",
            collection_id="test_curator_tag_collection_id",
            artifacts=[
                dict(
                    filename="test_filename",
                    filetype=DatasetArtifactFileType.H5AD.name,
                    user_submitted=True,
                    s3_uri=fake_s3_file,
                )
            ],
        )

    def test__update_collection__no_auth(self):
        collection_uuid = self.generate_collection(self.session).id
        response = self.app.patch(f"/curation/v1/collections/{collection_uuid}", data=json.dumps(self.test_collection))
        self.assertEqual(401, response.status_code)

    def test__update_collection__OK(self):
        collection_uuid = self.generate_collection(self.session).id
        response = self.app.patch(
            f"/curation/v1/collections/{collection_uuid}",
            data=json.dumps(self.test_collection),
            headers=self.get_auth_headers(),
        )
        self.assertEqual(200, response.status_code)

    def test__update_collection__Not_Owner(self):
        collection_uuid = self.generate_collection(self.session, owner="someone else").id
        response = self.app.patch(
            f"/curation/v1/collections/{collection_uuid}",
            data=json.dumps(self.test_collection),
            headers=self.get_auth_headers(),
        )
        self.assertEqual(403, response.status_code)

    def test__update_collection__Super_Curator(self):
        collection_uuid = self.generate_collection(self.session).id
        headers = self.make_super_curator_header()
        response = self.app.patch(
            f"/curation/v1/collections/{collection_uuid}", data=json.dumps(self.test_collection), headers=headers
        )
        self.assertEqual(200, response.status_code)


if __name__ == "__main__":
    unittest.main()