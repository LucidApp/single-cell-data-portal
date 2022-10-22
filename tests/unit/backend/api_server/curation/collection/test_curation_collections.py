import json
import unittest
from unittest.mock import patch, Mock

from backend.common.corpora_orm import (
    CollectionVisibility,
    ProcessingStatus,
    DbDataset,
    ValidationStatus,
)
from backend.portal.api.curation.v1.curation.collections.common import EntityColumns
from backend.common.providers.crossref_provider import CrossrefDOINotFoundException
from tests.unit.backend.api_server.base_api_test import BaseAuthAPITest, mock_assert_authorized_token


class TestAuthToken(BaseAuthAPITest):
    @patch("backend.portal.api.curation.v1.curation.collections.collection_id.datasets.upload_s3.sts_client")
    def test__generate_s3_credentials__OK(self, sts_client: Mock):
        def _test(token, is_super_curator: bool = False):
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

            response = self.app.get(f"/curation/v1/collections/{collection.id}/s3-upload-credentials", headers=headers)
            self.assertEqual(200, response.status_code)
            token_sub = mock_assert_authorized_token(token)["sub"]
            self.assertEqual(response.json["Bucket"], "cellxgene-dataset-submissions-test")
            if is_super_curator:
                self.assertEqual(response.json["UploadKeyPrefix"], f"super/{collection.id}/")
            else:
                self.assertEqual(response.json["UploadKeyPrefix"], f"{token_sub}/{collection.id}/")

        with self.subTest("collection owner"):
            _test("owner")

        with self.subTest("super curator"):
            _test("super", is_super_curator=True)

    def test__generate_s3_credentials__Not_Owner(self):
        collection = self.generate_collection(self.session, owner="not_test_user")
        response = self.app.get(
            f"/curation/v1/collections/{collection.id}/s3-upload-credentials", headers=self.make_owner_header()
        )
        self.assertEqual(403, response.status_code, msg=response.data)

    def test__generate_s3_credentials__Not_Private(self):
        collection = self.generate_collection(self.session, visibility=CollectionVisibility.PUBLIC.name)
        response = self.app.get(
            f"/curation/v1/collections/{collection.id}/s3-upload-credentials", headers=self.make_owner_header()
        )
        self.assertEqual(403, response.status_code)

    def test__generate_s3_credentials__No_Auth(self):
        collection = self.generate_collection(self.session, visibility=CollectionVisibility.PUBLIC.name)
        response = self.app.get(f"/curation/v1/collections/{collection.id}/s3-upload-credentials")
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
            "/curation/v1/collections", headers=self.make_owner_header(), data=json.dumps(self.test_collection)
        )
        self.assertIn("id", response.json.keys())
        self.assertEqual(201, response.status_code)

    def test__create_collection__InvalidParameters(self):
        requests = [
            (
                dict(
                    name="",
                    description="",
                    contact_name="",
                    contact_email="@email.com",
                    doi="10.111/not_curie_reference_format",
                ),
                [
                    {"name": "contact_email", "reason": "Invalid format."},
                    {"name": "description", "reason": "Cannot be blank."},
                    {"name": "name", "reason": "Cannot be blank."},
                    {"name": "contact_name", "reason": "Cannot be blank."},
                    {"name": "doi", "reason": "DOI must be a CURIE reference."},
                ],
                5,
            ),
            (
                dict(
                    name="Nonprintable\x0acharacters\x0bare_NOT_allowed_in_name",
                    description="But\x0anonprintable\x0acharacters\x0bARE_allowed_in_description",
                    contact_name="And\x0ain_contact_name",
                    contact_email="somebody@email.com",
                    doi="10.111/not_curie_reference_format",
                ),
                [
                    {"name": "name", "reason": "Invalid characters detected."},
                    {"name": "doi", "reason": "DOI must be a CURIE reference."},
                ],
                2,
            ),
        ]
        for body, expected_errors, num_expected_errors in requests:
            response = self.app.post(
                "/curation/v1/collections", headers=self.make_owner_header(), data=json.dumps(body)
            )
            self.assertEqual(400, response.status_code)
            for error in expected_errors:
                self.assertIn(error, response.json["invalid_parameters"])
            self.assertEqual(len(response.json["invalid_parameters"]), num_expected_errors)


class TestGetCollections(BaseAuthAPITest):
    def setUp(self):
        super().setUp()
        self.test_collection = dict(
            name="collection", description="description", contact_name="john doe", contact_email="johndoe@email.com"
        )

    def test__get_collections_no_auth__OK(self):
        res_no_auth = self.app.get("/curation/v1/collections")
        self.assertEqual(200, res_no_auth.status_code)
        self.assertEqual(6, len(res_no_auth.json))
        [self.assertEqual("PUBLIC", c["visibility"]) for c in res_no_auth.json]

    def test__get_collections_with_auth__OK(self):
        res_auth = self.app.get("/curation/v1/collections", headers=self.make_owner_header())
        with self.subTest("The 'revising_in' attribute is None for unauthorized public collections"):
            conditions_tested = 0
            for c in res_auth.json:
                if c["id"] in (
                    "test_collection_id_public_for_revision_one",
                    "test_collection_id_public_for_revision_two",
                ):
                    conditions_tested += 1
                    self.assertIsNone(c["revising_in"])
            self.assertEqual(2, conditions_tested)
        with self.subTest("The 'revising_in' attribute is None for collections which lack a revision"):
            conditions_tested = 0
            for c in res_auth.json:
                if c["id"] in (
                    "test_collection_id_public",
                    "test_collection_with_link",
                    "test_collection_with_link_and_dataset_changes",
                ):
                    conditions_tested += 1
                    self.assertIsNone(c["revising_in"])
            self.assertEqual(3, conditions_tested)
        with self.subTest("The 'revising_in' attribute is equal to the id of the revision Collection"):
            conditions_tested = 0
            for c in res_auth.json:
                if c["id"] == "test_collection_id":
                    conditions_tested += 1
                    self.assertEqual("test_collection_id_revision", c["revising_in"])
            self.assertTrue(1, conditions_tested)
        with self.subTest("Datasets in a revision contain a reference to their published counterpart, if it exists"):
            conditions_tested = 0
            for c in res_auth.json:
                if c["id"] == "test_collection_id_revision":
                    for d in c["datasets"]:
                        if d["id"] == "test_publish_revision_with_links__revision_dataset":
                            conditions_tested += 1
                            self.assertEqual("test_dataset_id", d["revision_of"])
            self.assertTrue(1, conditions_tested)

    def test__get_collections_no_auth_visibility_private__OK(self):
        params = {"visibility": "PRIVATE"}
        res_private = self.app.get("/curation/v1/collections", query_string=params)
        self.assertEqual(403, res_private.status_code)

    def test__get_collections_no_auth_visibility_public__OK(self):
        params = {"visibility": "PUBLIC"}
        res_public = self.app.get("/curation/v1/collections", query_string=params)
        self.assertEqual(200, res_public.status_code)
        self.assertEqual(6, len(res_public.json))

    def test__get_a_curators_collections(self):
        curator_name = "John Smith"
        self.generate_collection(self.session, curator_name="Not Smith")
        self.generate_collection(self.session, curator_name=curator_name, visibility=CollectionVisibility.PUBLIC)
        self.generate_collection(self.session, curator_name=curator_name, visibility=CollectionVisibility.PRIVATE)

        def _test(query_param, headers, expected_number_of_results):
            response = self.app.get("/curation/v1/collections", query_string=query_param, headers=headers)
            self.assertEqual(200, response.status_code)
            self.assertEqual(expected_number_of_results, len(response.json))
            for collection in response.json:
                self.assertEqual(curator_name, collection["curator_name"])

        visibilities = ["PUBLIC", "PRIVATE"]
        for visibility in visibilities:
            params = {"curator": curator_name, "visibility": visibility}
            with self.subTest(f"regular curators can't search by curator {visibility}"):
                response = self.app.get(
                    "/curation/v1/collections", query_string=params, headers=self.make_not_owner_header()
                )
                self.assertEqual(403, response.status_code)
            with self.subTest(f"users can't search by curator {visibility}"):
                response = self.app.get("/curation/v1/collections", query_string=params)
                self.assertEqual(403, response.status_code)

        with self.subTest("Searching for a curator that doesn't exists return 0 collections"):
            _test({"curator": "Not A Curator"}, self.make_super_curator_header(), 0)
        with self.subTest("super curators can search public collections by curator"):
            _test({"curator": curator_name}, self.make_super_curator_header(), 1)
        with self.subTest("super curators can search private collections by curator"):
            _test({"curator": curator_name, "visibility": "PRIVATE"}, self.make_super_curator_header(), 1)

    def test__get_only_public_collections_with_auth__OK(self):
        params = {"visibility": "PUBLIC"}
        res = self.app.get("/curation/v1/collections", query_string=params, headers=self.make_owner_header())
        self.assertEqual(200, res.status_code)
        self.assertEqual(6, len(res.json))
        [self.assertEqual("PUBLIC", c["visibility"]) for c in res.json]

    def test__get_only_private_collections_with_auth__OK(self):
        second_collection = self.generate_collection(self.session)
        for status in (ProcessingStatus.PENDING, ProcessingStatus.SUCCESS):
            self.generate_dataset(
                self.session,
                collection_id=second_collection.id,
                processing_status={"processing_status": status},
            ).id
        third_collection = self.generate_collection(self.session)
        for status in (ProcessingStatus.INITIALIZED, ProcessingStatus.SUCCESS):
            self.generate_dataset(
                self.session,
                collection_id=third_collection.id,
                processing_status={"processing_status": status},
            ).id
        params = {"visibility": "PRIVATE"}
        res = self.app.get("/curation/v1/collections", query_string=params, headers=self.make_owner_header())
        conditions_tested = 0
        with self.subTest("Summary collection-level processing statuses are accurate"):
            for collection in res.json:
                if collection["id"] in (second_collection.id, third_collection.id):
                    self.assertEqual(collection["processing_status"], "PENDING")
                    conditions_tested += 1
                else:
                    self.assertEqual(collection["processing_status"], "SUCCESS")
        self.assertEqual(2, conditions_tested)
        self.assertEqual(200, res.status_code)
        self.assertEqual(3, len(res.json))
        [self.assertEqual("PRIVATE", c["visibility"]) for c in res.json]

    def test__verify_expected_public_collection_fields(self):
        collection = self.generate_collection(
            self.session,
            visibility=CollectionVisibility.PUBLIC.name,
            links=[
                {
                    "link_name": "test_raw_data_link_name",
                    "link_type": "RAW_DATA",
                    "link_url": "http://test_raw_data_url.place",
                }
            ],
        )
        self.generate_dataset(self.session, collection=collection)
        res = self.app.get("/curation/v1/collections")
        self.assertEqual(200, res.status_code)
        for resp_collection in res.json:
            if resp_collection["id"] is collection.id:
                break

        self.check_fields(EntityColumns.link_cols, resp_collection["links"][0], "links")
        self.check_fields(EntityColumns.dataset_preview_cols, resp_collection["datasets"][0], "datasets")

        collections_cols = EntityColumns.collections_cols.copy()
        collections_cols.remove("owner")
        collections_cols.remove("tombstone")
        collections_cols.append("processing_status")
        collections_cols.append("collection_url")
        collections_cols.append("doi")
        self.check_fields(collections_cols, resp_collection, "collection")

    def test__verify_expected_private_collection_fields(self):
        collection = self.generate_collection(
            self.session,
            visibility=CollectionVisibility.PRIVATE.name,
            links=[
                {
                    "link_name": "test_raw_data_link_name",
                    "link_type": "RAW_DATA",
                    "link_url": "http://test_raw_data_url.place",
                }
            ],
        )
        self.generate_dataset(self.session, collection=collection)
        params = {"visibility": "PRIVATE"}

        def _test(owner):
            if owner:
                header = self.make_owner_header()
                subtest_prefix = "owner"
            else:
                header = self.make_not_owner_header()
                subtest_prefix = "not_owner"
            res = self.app.get("/curation/v1/collections", query_string=params, headers=header)
            self.assertEqual(200, res.status_code)
            for resp_collection in res.json:
                if resp_collection["id"] is collection.id:
                    break

            self.check_fields(EntityColumns.link_cols, resp_collection["links"][0], f"{subtest_prefix}:links")
            self.check_fields(
                EntityColumns.dataset_preview_cols, resp_collection["datasets"][0], f"{subtest_prefix}:datasets"
            )

            collections_cols = EntityColumns.collections_cols.copy()
            collections_cols.remove("tombstone")
            collections_cols.remove("owner")
            collections_cols.append("processing_status")
            collections_cols.append("collection_url")
            collections_cols.append("doi")
            self.check_fields(collections_cols, resp_collection, f"{subtest_prefix}:collection")

        _test(True)

    def check_fields(self, fields: list, response: dict, entity: str):
        for key in fields:
            with self.subTest(f"{entity}:{key}"):
                self.assertIn(key, response.keys())
                response.pop(key)
        with self.subTest(f"No Extra fields in {entity}"):
            self.assertFalse(response)

    def test__no_tombstoned_collections_or_datasets_included(self):
        second_collection = self.generate_collection(
            self.session, tombstone=False, name="second collection", visibility=CollectionVisibility.PUBLIC
        )
        self.generate_dataset(self.session, collection_id=second_collection.id)
        self.generate_dataset(self.session, collection_id=second_collection.id, tombstone=True)
        tombstoned_collection = self.generate_collection(
            self.session, tombstone=True, name="second collection", visibility=CollectionVisibility.PUBLIC
        )
        self.generate_dataset(self.session, collection_id=tombstoned_collection.id, tombstone=True)

        res = self.app.get("/curation/v1/collections", headers=self.make_owner_header())

        contains_tombstoned_collection_flag = False
        for collection in res.json:
            if collection["id"] == second_collection.id:
                self.assertEqual(1, len(collection["datasets"]))
            if collection["id"] == tombstoned_collection.id:
                contains_tombstoned_collection_flag = True
        self.assertEqual(False, contains_tombstoned_collection_flag)


class TestGetCollectionID(BaseAuthAPITest):
    expected_body = {
        "collection_url": "http://frontend.corporanet.local:3000/collections/test_collection_id",
        "contact_email": "somebody@chanzuckerberg.com",
        "contact_name": "Some Body",
        "curator_name": "",
        "datasets": [
            {
                "assay": [{"label": "test_assay", "ontology_term_id": "test_obo"}],
                "batch_condition": ["batchA", "batchB"],
                "cell_count": None,
                "cell_type": [{"label": "test_cell_type", "ontology_term_id": "test_opo"}],
                "dataset_assets": [{"filename": "test_filename", "filetype": "H5AD"}],
                "development_stage": [{"label": "test_development_stage", "ontology_term_id": "test_obo"}],
                "disease": [
                    {"label": "test_disease", "ontology_term_id": "test_obo"},
                    {"label": "test_disease2", "ontology_term_id": "test_obp"},
                    {"label": "test_disease3", "ontology_term_id": "test_obq"},
                ],
                "donor_id": ["donor_1", "donor_2"],
                "self_reported_ethnicity": [{"label": "test_ethnicity", "ontology_term_id": "test_obo"}],
                "explorer_url": "test_url",
                "id": "test_dataset_id",
                "is_primary_data": [True],
                "mean_genes_per_cell": 0.0,
                "title": "test_dataset_name",
                "organism": [{"label": "test_organism", "ontology_term_id": "test_obo"}],
                "processing_status": "PENDING",
                "revised_at": None,
                "revision": 0,
                "revision_of": None,
                "schema_version": "3.0.0",
                "sex": [
                    {"label": "test_sex", "ontology_term_id": "test_obo"},
                    {"label": "test_sex2", "ontology_term_id": "test_obp"},
                ],
                "suspension_type": ["nucleus"],
                "tissue": [{"label": "test_tissue", "ontology_term_id": "test_obo"}],
                "tombstone": False,
                "x_approximate_distribution": "NORMAL",
            }
        ],
        "description": "test_description",
        "doi": "",
        "id": "test_collection_id",
        "links": [
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
        "processing_status": "PENDING",
        "published_at": None,
        "publisher_metadata": None,
        "revised_at": None,
        "revision_of": None,
        "revising_in": None,
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
        self.assertDictEqual(self.expected_body, res_body)  # Confirm dict has been packaged in list
        self.assertEqual(json.dumps(self.expected_body, sort_keys=True), json.dumps(res_body))

    def test__get_private_collection__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_revision")
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id_revision", res.json["id"])

    def test__get_collection_with_dataset_failing_validation(self):
        collection = self.generate_collection(
            self.session,
            visibility=CollectionVisibility.PRIVATE.name,
        )
        dataset = self.generate_dataset(
            self.session,
            collection=collection,
            processing_status={
                "processing_status": ProcessingStatus.FAILURE,
                "validation_status": ValidationStatus.INVALID,
                "validation_message": "test message",
            },
        )
        res = self.app.get(f"/curation/v1/collections/{collection.id}")
        self.assertEqual("FAILURE", res.json["processing_status"])
        actual_dataset = res.json["datasets"][0]
        self.assertEqual(dataset.id, actual_dataset["id"])
        self.assertEqual("VALIDATION_FAILURE", actual_dataset["processing_status"])
        self.assertEqual("test message", actual_dataset["processing_status_detail"])

    def test__get_collection_with_dataset_failing_pipeline(self):
        collection = self.generate_collection(
            self.session,
            visibility=CollectionVisibility.PRIVATE.name,
        )
        dataset = self.generate_dataset(
            self.session, collection=collection, processing_status={"processing_status": ProcessingStatus.FAILURE}
        )
        res = self.app.get(f"/curation/v1/collections/{collection.id}")
        self.assertEqual("FAILURE", res.json["processing_status"])
        actual_dataset = res.json["datasets"][0]
        self.assertEqual(dataset.id, actual_dataset["id"])
        self.assertEqual("PIPELINE_FAILURE", actual_dataset["processing_status"])

    def test__get_nonexistent_collection__403(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_nonexistent")
        self.assertEqual(403, res.status_code)

    def test__get_tombstoned_collection__403(self):
        tombstoned_collection = self.generate_collection(
            self.session, tombstone=True, name="tombstoned collection", visibility=CollectionVisibility.PUBLIC
        )
        self.generate_dataset(self.session, collection_id=tombstoned_collection.id, tombstone=True)
        res = self.app.get(f"/curation/v1/collections/{tombstoned_collection.id}")
        self.assertEqual(403, res.status_code)

    def test_get_collection_with_no_datasets(self):
        collection = self.generate_collection(self.session, name="No Datasets", visibility=CollectionVisibility.PUBLIC)
        res = self.app.get(f"/curation/v1/collections/{collection.id}")
        self.assertEqual(200, res.status_code)
        self.assertEqual(res.json["processing_status"], None)

    def test__get_collection_with_tombstoned_datasets__OK(self):
        collection = self.generate_collection(
            self.session, tombstone=False, name="collection", visibility=CollectionVisibility.PUBLIC
        )
        self.generate_dataset(self.session, collection_id=collection.id, tombstone=False)
        self.generate_dataset(self.session, collection_id=collection.id, tombstone=True)
        res = self.app.get(f"/curation/v1/collections/{collection.id}")
        self.assertEqual(1, len(res.json["datasets"]))

    def test__get_public_collection_with_auth_access_type_write__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id", headers=self.make_owner_header())
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id", res.json["id"])

    def test__get_public_collection_with_auth_access_type_read__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_not_owner", headers=self.make_owner_header())
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id_not_owner", res.json["id"])

    def test__get_private_collection_with_auth_access_type_write__OK(self):
        res = self.app.get("/curation/v1/collections/test_collection_id_revision", headers=self.make_owner_header())
        self.assertEqual(200, res.status_code)
        self.assertEqual("test_collection_id_revision", res.json["id"])

    def test__get_collectoin_with_x_approximate_distribution_none__OK(self):
        collection = self.generate_collection(self.session)
        self.generate_dataset(self.session, x_approximate_distribution=None, collection=collection)
        res = self.app.get(f"/curation/v1/collections/{collection.id}", headers=self.make_owner_header())
        self.assertEqual(200, res.status_code)
        self.assertIsNone(res.json["datasets"][0]["x_approximate_distribution"])


class TestPatchCollectionID(BaseAuthAPITest):
    def setUp(self):
        super().setUp()
        self.test_collection = dict(
            name="collection", description="description", contact_name="john doe", contact_email="johndoe@email.com"
        )

    def test__update_collection__no_auth(self):
        collection_id = self.generate_collection(self.session).id
        response = self.app.patch(f"/curation/v1/collections/{collection_id}", data=json.dumps(self.test_collection))
        self.assertEqual(401, response.status_code)

    def test__update_collection__OK(self):
        collection_id = self.generate_collection(self.session).id
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}",
            data=json.dumps(self.test_collection),
            headers=self.make_owner_header(),
        )
        self.assertEqual(200, response.status_code)

    def test__update_collection_partial_data__OK(self):
        description = "a description"
        contact_name = "first last"
        contact_email = "name@server.domain"
        links = [
            {"link_name": "name", "link_type": "RAW_DATA", "link_url": "http://test_link.place"},
        ]
        publisher_metadata = {
            "authors": [{"name": "First Last", "given": "First", "family": "Last"}],
            "journal": "Journal of Anamolous Results",
            "published_year": 2022,
            "published_month": 1,
        }
        collection_id = self.generate_collection(
            self.session,
            description=description,
            contact_name=contact_name,
            contact_email=contact_email,
            links=links,
            publisher_metadata=publisher_metadata,
        ).id
        new_name = "A new name, and only a new name"
        metadata = {"name": new_name}
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}",
            data=json.dumps(metadata),
            headers=self.make_owner_header(),
        )
        self.assertEqual(200, response.status_code)
        response = self.app.get(f"curation/v1/collections/{collection_id}")
        self.assertEqual(new_name, response.json["name"])
        self.assertEqual(description, response.json["description"])
        self.assertEqual(contact_name, response.json["contact_name"])
        self.assertEqual(contact_email, response.json["contact_email"])
        self.assertEqual(links, response.json["links"])
        self.assertEqual(publisher_metadata, response.json["publisher_metadata"])

    def test_update_collection_with_empty_required_fields(self):
        tests = [dict(description=""), dict(contact_name=""), dict(contact_email=""), dict(name="")]

        collection_id = self.generate_collection(self.session).id
        for test in tests:
            with self.subTest(test):
                response = self.app.patch(
                    f"/curation/v1/collections/{collection_id}",
                    data=json.dumps(test),
                    headers=self.make_owner_header(),
                )
                self.assertEqual(400, response.status_code)

    def test__update_collection__links__OK(self):
        name = "partial updates test collection"
        links = [
            {"link_name": "name", "link_type": "RAW_DATA", "link_url": "http://test_link.place"},
        ]
        new_links = [
            {"link_name": "new link", "link_type": "RAW_DATA", "link_url": "http://brand_new_link.place"},
        ]

        links_configurations = (
            ("With links already in place; new links replace old", links, new_links, 200, new_links),
            ("With no links in place; new links get added", None, new_links, 200, new_links),
            ("With links in place, but empty request; no changes are made", links, None, 200, links),
            ("With links in place, empty array passed; BAD REQUEST 400", links, [], 400, links),
        )

        for test_title, initial_links, new_links, expected_status_code, expected_links in links_configurations:
            with self.subTest(test_title):
                collection_id = self.generate_collection(self.session, name=name, links=initial_links).id
                original_collection = self.app.get(f"curation/v1/collections/{collection_id}").json
                self.assertEqual(initial_links if initial_links else [], original_collection["links"])
                metadata = {"links": new_links} if new_links is not None else {}
                response = self.app.patch(
                    f"/curation/v1/collections/{collection_id}",
                    data=json.dumps(metadata),
                    headers=self.make_owner_header(),
                )
                self.assertEqual(expected_status_code, response.status_code)
                if expected_status_code == 200:
                    self.assertEqual(name, response.json["name"])
                    self.assertEqual(expected_links, response.json["links"])

    def test__update_collection__doi__OK(self):
        initial_doi = "12.3456/doi_curie_reference"
        links = [
            {"link_name": "new doi", "link_type": "DOI", "link_url": initial_doi},
        ]
        new_doi = "10.1016"  # a real DOI (CURIE reference)
        collection_id = self.generate_collection(self.session, links=links).id
        original_collection = self.app.get(f"curation/v1/collections/{collection_id}").json
        self.assertEqual(initial_doi, original_collection["doi"])
        metadata = {"doi": new_doi}
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}",
            json=metadata,
            headers=self.make_owner_header(),
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(new_doi, response.json["doi"])

    def test__update_collection__doi_is_not_CURIE_reference__BAD_REQUEST(self):
        links = [
            {"link_name": "doi", "link_type": "DOI", "link_url": "http://doi.doi/10.1011/something"},
        ]
        collection = self.generate_collection(self.session, links=links)
        collection_id = collection.id
        original_collection = self.app.get(f"curation/v1/collections/{collection_id}").json

        metadata = {"doi": "https://doi.org/10.1016"}
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}",
            json=metadata,
            headers=self.make_owner_header(),
        )
        self.assertEqual(400, response.status_code)
        original_collection_unchanged = self.app.get(f"curation/v1/collections/{collection_id}").json
        self.assertEqual(original_collection["doi"], original_collection_unchanged["doi"])

    def test__update_collection__doi_does_not_exist__BAD_REQUEST(self):
        name = "bad doi update test collection"
        links = [
            {"link_name": "name", "link_type": "RAW_DATA", "link_url": "http://test_link.place"},
            {"link_name": "doi", "link_type": "DOI", "link_url": "http://doi.doi/10.1011/something"},
        ]
        new_links = [
            {"link_name": "new link", "link_type": "RAW_DATA", "link_url": "http://brand_new_link.place"},
        ]
        publisher_metadata = {
            "authors": [{"name": "First Last", "given": "First", "family": "Last"}],
            "journal": "Journal of Anamolous Results",
            "published_year": 2022,
            "published_month": 1,
        }
        with patch(
            "backend.common.providers.crossref_provider.CrossrefProvider.fetch_metadata",
            side_effect=CrossrefDOINotFoundException(),
        ):

            collection = self.generate_collection(
                self.session, name=name, links=links, publisher_metadata=publisher_metadata
            )
            collection_id = collection.id
            original_collection = self.app.get(f"curation/v1/collections/{collection_id}").json

            # Only compare to first item in links list because "DOI" type gets removed from Curator API response
            self.assertEqual(links[:1], original_collection["links"])
            metadata = {"links": new_links, "doi": "10.1016/bad_doi"}
            response = self.app.patch(
                f"/curation/v1/collections/{collection_id}",
                data=json.dumps(metadata),
                headers=self.make_owner_header(),
            )
            self.assertEqual(400, response.status_code)
            original_collection_unchanged = self.app.get(f"curation/v1/collections/{collection_id}").json
            self.assertEqual(name, original_collection_unchanged["name"])
            # Only compare to first item in links list because "DOI" type gets removed from Curator API response
            self.assertEqual(links[:1], original_collection_unchanged["links"])
            self.assertEqual(publisher_metadata, original_collection_unchanged["publisher_metadata"])

    def test__update_collection__Not_Owner(self):
        collection_id = self.generate_collection(self.session, owner="someone else").id
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}",
            data=json.dumps(self.test_collection),
            headers=self.make_owner_header(),
        )
        self.assertEqual(403, response.status_code)

    def test__update_collection__Super_Curator(self):
        collection_id = self.generate_collection(self.session).id
        headers = self.make_super_curator_header()
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}", data=json.dumps(self.test_collection), headers=headers
        )
        self.assertEqual(200, response.status_code)

    def test__update_public_collection_owner__405(self):
        collection_id = self.generate_collection(self.session, visibility=CollectionVisibility.PUBLIC).id
        headers = self.make_super_curator_header()
        response = self.app.patch(
            f"/curation/v1/collections/{collection_id}", data=json.dumps(self.test_collection), headers=headers
        )
        self.assertEqual(405, response.status_code)
        self.assertEqual(
            "Directly editing a public Collection is not allowed; you must create a revision.",
            json.loads(response.text)["detail"],
        )


if __name__ == "__main__":
    unittest.main()