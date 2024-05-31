from unittest.mock import Mock

from backend.layers.common.entities import CollectionVersionId


class TestCollectionMigrate:
    def test_can_publish_true(self, schema_migrate_and_collections):
        schema_migrate, collections = schema_migrate_and_collections
        schema_migrate._store_sfn_response = Mock(wraps=schema_migrate._store_sfn_response)
        schema_migrate.schema_version = "0.0.0"
        published = collections["published"][0]
        collection_version_id = CollectionVersionId()
        schema_migrate.business_logic.create_collection_version.return_value = Mock(version_id=collection_version_id)
        datasets = [
            {
                "dataset_id": dataset.dataset_id.id,
                "dataset_version_id": dataset.version_id.id,
                "collection_url": f"https://collections_domain/collections/{published.collection_id.id}",
                "execution_id": "test-execution-arn",
            }
            for dataset in published.datasets
        ]
        response, response_for_publish_and_cleanup, response_for_span_datasets = schema_migrate.collection_migrate(
            published.collection_id.id, published.version_id.id, True
        )
        schema_migrate._store_sfn_response.assert_any_call(
            "publish_and_cleanup", published.collection_id.id, response_for_publish_and_cleanup
        )
        schema_migrate._store_sfn_response.assert_any_call(
            "span_datasets", published.collection_id.id, response_for_span_datasets
        )
        assert response_for_publish_and_cleanup["collection_version_id"] == collection_version_id.id
        assert (
            response_for_publish_and_cleanup["collection_url"]
            == f"https://collections_domain/collections/{published.collection_id.id}"
        )
        assert "key_name" in response
        for i in range(len(response_for_span_datasets)):
            assert response_for_span_datasets[i].pop("collection_version_id") == collection_version_id.id
            assert response_for_span_datasets[i].pop("collection_id") == published.collection_id.id
            assert response_for_span_datasets[i] == datasets[i]

    def test_can_publish_false(self, schema_migrate_and_collections):
        schema_migrate, collections = schema_migrate_and_collections
        schema_migrate._store_sfn_response = Mock(wraps=schema_migrate._store_sfn_response)
        schema_migrate.schema_version = "0.0.0"
        private = collections["private"][0]
        datasets = [
            {
                "dataset_id": dataset.dataset_id.id,
                "dataset_version_id": dataset.version_id.id,
                "collection_url": f"https://collections_domain/collections/{private.collection_id.id}",
                "execution_id": "test-execution-arn",
            }
            for dataset in private.datasets
        ]
        response, response_for_publish_and_cleanup, response_for_span_datasets = schema_migrate.collection_migrate(
            private.collection_id.id, private.version_id.id, False
        )
        schema_migrate._store_sfn_response.assert_any_call(
            "publish_and_cleanup", private.collection_id.id, response_for_publish_and_cleanup
        )
        schema_migrate._store_sfn_response.assert_any_call(
            "span_datasets", private.collection_id.id, response_for_span_datasets
        )

        # verify response_for_publish_and_cleanup
        assert response_for_publish_and_cleanup["collection_version_id"] == private.version_id.id
        assert (
            response_for_publish_and_cleanup["collection_url"]
            == f"https://collections_domain/collections/{private.collection_id.id}"
        )

        # Verify response
        assert "key_name" in response
        assert response["collection_version_id"] == private.version_id.id
        assert response["execution_id"] == "test-execution-arn"

        # Verify response_for_span_datasets
        for i in range(len(response_for_span_datasets)):
            assert response_for_span_datasets[i].pop("collection_version_id") == private.version_id.id
            assert response_for_span_datasets[i].pop("collection_id") == private.collection_id.id
            assert response_for_span_datasets[i] == datasets[i]

    def test_can_publish_false_and_no_datasets(self, schema_migrate_and_collections):
        schema_migrate, collections = schema_migrate_and_collections
        schema_migrate._store_sfn_response = Mock(wraps=schema_migrate._store_sfn_response)
        schema_migrate.schema_version = "0.0.0"
        published = collections["published"][0]
        published.datasets = []
        schema_migrate.business_logic.create_collection_version.return_value = Mock(version_id=CollectionVersionId())
        response, response_for_publish_and_cleanup, response_for_span_datasets = schema_migrate.collection_migrate(
            published.collection_id.id, published.version_id.id, False
        )
        schema_migrate._store_sfn_response.assert_called_once_with(
            "publish_and_cleanup", published.collection_id.id, response_for_publish_and_cleanup
        )

        # verify response_for_publish_and_cleanup
        assert response_for_publish_and_cleanup["collection_version_id"] == published.version_id.id
        assert (
            response_for_publish_and_cleanup["collection_url"]
            == f"https://collections_domain/collections/{published.collection_id.id}"
        )
        # verify response_for_span_datasets
        assert not response_for_span_datasets

        # verify response
        assert "key_name" not in response
        assert response["collection_version_id"] == published.version_id.id
        assert response["execution_id"] == "test-execution-arn"

    def test_can_publish_true_and_filtered_schema_version(self, schema_migrate_and_collections):
        schema_migrate, collections = schema_migrate_and_collections
        schema_migrate._store_sfn_response = Mock(wraps=schema_migrate._store_sfn_response)
        published = collections["published"][0]
        schema_migrate.business_logic.create_collection_version.return_value = Mock(version_id=CollectionVersionId())
        response, response_for_publish_and_cleanup, response_for_span_datasets = schema_migrate.collection_migrate(
            published.collection_id.id, published.version_id.id, False
        )
        schema_migrate._store_sfn_response.assert_called_once_with(
            "publish_and_cleanup", published.collection_id.id, response_for_publish_and_cleanup
        )

        # verify response_for_publish_and_cleanup
        assert response_for_publish_and_cleanup["collection_version_id"] == published.version_id.id
        assert (
            response_for_publish_and_cleanup["collection_url"]
            == f"https://collections_domain/collections/{published.collection_id.id}"
        )

        # verify response_for_span_datasets
        assert not response_for_span_datasets

        # verify response
        assert "key_name" not in response
        assert response["collection_version_id"] == published.version_id.id
        assert response["execution_id"] == "test-execution-arn"

    def test_no_datasets(self, schema_migrate_and_collections):
        schema_migrate, collections = schema_migrate_and_collections
        schema_migrate._store_sfn_response = Mock(wraps=schema_migrate._store_sfn_response)
        published = collections["published"][0]
        published.datasets = []
        schema_migrate.business_logic.create_collection_version.return_value = Mock(version_id=CollectionVersionId())
        response, response_for_publish_and_cleanup, response_for_span_datasets = schema_migrate.collection_migrate(
            published.collection_id.id, published.version_id.id, False
        )
        schema_migrate._store_sfn_response.assert_called_once_with(
            "publish_and_cleanup", published.collection_id.id, response_for_publish_and_cleanup
        )

        # verify response_for_publish_and_cleanup
        assert response_for_publish_and_cleanup["collection_version_id"] == published.version_id.id
        assert (
            response_for_publish_and_cleanup["collection_url"]
            == f"https://collections_domain/collections/{published.collection_id.id}"
        )

        # verify response_for_span_datasets
        assert not response_for_span_datasets

        # verify response
        assert "key_name" not in response
        assert response["collection_version_id"] == published.version_id.id
        assert response["execution_id"] == "test-execution-arn"
