import os
from collections import defaultdict

import orjson
from astrapy import DataAPIClient
from astrapy.admin import parse_api_endpoint
from astrapy.exceptions import CollectionNotFoundException
from langchain_astradb import AstraDBVectorStore

from langflow.base.vectorstores.model import LCVectorStoreComponent, check_cached_vector_store
from langflow.helpers import docs_to_data
from langflow.inputs import DictInput, FloatInput, MessageTextInput, NestedDictInput
from langflow.io import (
    BoolInput,
    DataInput,
    DropdownInput,
    HandleInput,
    IntInput,
    MultilineInput,
    SecretStrInput,
    StrInput,
)
from langflow.schema import Data


class AstraDBVectorStoreComponent(LCVectorStoreComponent):
    display_name: str = "Astra DB"
    description: str = "Implementation of Vector Store using Astra DB with search capabilities"
    documentation: str = "https://docs.langflow.org/starter-projects-vector-store-rag"
    name = "AstraDB"
    icon: str = "AstraDB"

    _cached_vector_store: AstraDBVectorStore | None = None

    def list_collections(self):
        client = DataAPIClient(token=self.token)

        database = client.get_database(
            self.api_endpoint,
            token=self.token,
        )

        return database.list_collections()

    def _initialize_collection_options(self):
        try:
            collections = [collection.name for collection in self.list_collections()]
        except (CollectionNotFoundException, ConnectionError, ValueError) as _:
            collections = []

        return [*collections, "+ Create new collection"]

    VECTORIZE_PROVIDERS_MAPPING = defaultdict(
        list,
        {
            "Azure OpenAI": [
                "azureOpenAI",
                ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
            ],
            "Hugging Face - Dedicated": ["huggingfaceDedicated", ["endpoint-defined-model"]],
            "Hugging Face - Serverless": [
                "huggingface",
                [
                    "sentence-transformers/all-MiniLM-L6-v2",
                    "intfloat/multilingual-e5-large",
                    "intfloat/multilingual-e5-large-instruct",
                    "BAAI/bge-small-en-v1.5",
                    "BAAI/bge-base-en-v1.5",
                    "BAAI/bge-large-en-v1.5",
                ],
            ],
            "Jina AI": [
                "jinaAI",
                [
                    "jina-embeddings-v2-base-en",
                    "jina-embeddings-v2-base-de",
                    "jina-embeddings-v2-base-es",
                    "jina-embeddings-v2-base-code",
                    "jina-embeddings-v2-base-zh",
                ],
            ],
            "Mistral AI": ["mistral", ["mistral-embed"]],
            "Nvidia": ["nvidia", ["NV-Embed-QA"]],
            "OpenAI": ["openai", ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]],
            "Upstage": ["upstageAI", ["solar-embedding-1-large"]],
            "Voyage AI": [
                "voyageAI",
                ["voyage-large-2-instruct", "voyage-law-2", "voyage-code-2", "voyage-large-2", "voyage-2"],
            ],
        },
    )

    inputs = [
        SecretStrInput(
            name="token",
            display_name="Astra DB Application Token",
            info="Authentication token for accessing Astra DB.",
            value="ASTRA_DB_APPLICATION_TOKEN",
            required=True,
            advanced=os.getenv("ASTRA_ENHANCED", "false").lower() == "true",
        ),
        SecretStrInput(
            name="api_endpoint",
            display_name="Database" if os.getenv("ASTRA_ENHANCED", "false").lower() == "true" else "API Endpoint",
            info="API endpoint URL for the Astra DB service.",
            value="ASTRA_DB_API_ENDPOINT",
            required=True,
        ),
        DropdownInput(
            name="collection_name",
            display_name="Collection",
            info="The name of the collection within Astra DB where the vectors will be stored.",
            required=True,
            real_time_refresh=True,
            refresh_button=True,
            options=["+ Create new collection"],
            value="+ Create new collection",
        ),
        StrInput(
            name="collection_name_new",
            display_name="Collection Name",
            info="Name of the new collection to create.",
            advanced=False,
            required=True,
        ),
        StrInput(
            name="keyspace",
            display_name="Keyspace",
            info="Optional keyspace within Astra DB to use for the collection.",
            advanced=True,
        ),
        MultilineInput(
            name="search_input",
            display_name="Search Input",
        ),
        IntInput(
            name="number_of_results",
            display_name="Number of Results",
            info="Number of results to return.",
            advanced=True,
            value=4,
        ),
        DropdownInput(
            name="search_type",
            display_name="Search Type",
            info="Search type to use",
            options=["Similarity", "Similarity with score threshold", "MMR (Max Marginal Relevance)"],
            value="Similarity",
            advanced=True,
        ),
        FloatInput(
            name="search_score_threshold",
            display_name="Search Score Threshold",
            info="Minimum similarity score threshold for search results. "
            "(when using 'Similarity with score threshold')",
            value=0,
            advanced=True,
        ),
        NestedDictInput(
            name="advanced_search_filter",
            display_name="Search Metadata Filter",
            info="Optional dictionary of filters to apply to the search query.",
            advanced=True,
        ),
        DictInput(
            name="search_filter",
            display_name="[DEPRECATED] Search Metadata Filter",
            info="Deprecated: use advanced_search_filter. Optional dictionary of filters to apply to the search query.",
            advanced=True,
            list=True,
        ),
        DataInput(
            name="ingest_data",
            display_name="Ingest Data",
        ),
        DropdownInput(
            name="embedding_choice",
            display_name="Embedding Model or Astra Vectorize",
            info="Determines whether to use Astra Vectorize for the collection.",
            options=["Embedding Model", "Astra Vectorize"],
            real_time_refresh=True,
            value="Embedding Model",
        ),
        HandleInput(
            name="embedding_model",
            display_name="Embedding Model",
            input_types=["Embeddings"],
            info="Allows an embedding model configuration.",
        ),
        DropdownInput(
            name="metric",
            display_name="Metric",
            info="Optional distance metric for vector comparisons in the vector store.",
            options=["cosine", "dot_product", "euclidean"],
            value="cosine",
            advanced=True,
        ),
        IntInput(
            name="batch_size",
            display_name="Batch Size",
            info="Optional number of data to process in a single batch.",
            advanced=True,
        ),
        IntInput(
            name="bulk_insert_batch_concurrency",
            display_name="Bulk Insert Batch Concurrency",
            info="Optional concurrency level for bulk insert operations.",
            advanced=True,
        ),
        IntInput(
            name="bulk_insert_overwrite_concurrency",
            display_name="Bulk Insert Overwrite Concurrency",
            info="Optional concurrency level for bulk insert operations that overwrite existing data.",
            advanced=True,
        ),
        IntInput(
            name="bulk_delete_concurrency",
            display_name="Bulk Delete Concurrency",
            info="Optional concurrency level for bulk delete operations.",
            advanced=True,
        ),
        DropdownInput(
            name="setup_mode",
            display_name="Setup Mode",
            info="Configuration mode for setting up the vector store, with options like 'Sync' or 'Off'.",
            options=["Sync", "Off"],
            advanced=True,
            value="Sync",
        ),
        BoolInput(
            name="pre_delete_collection",
            display_name="Pre Delete Collection",
            info="Boolean flag to determine whether to delete the collection before creating a new one.",
            advanced=True,
        ),
        StrInput(
            name="metadata_indexing_include",
            display_name="Metadata Indexing Include",
            info="Optional list of metadata fields to include in the indexing.",
            list=True,
            advanced=True,
        ),
        StrInput(
            name="metadata_indexing_exclude",
            display_name="Metadata Indexing Exclude",
            info="Optional list of metadata fields to exclude from the indexing.",
            list=True,
            advanced=True,
        ),
        StrInput(
            name="collection_indexing_policy",
            display_name="Collection Indexing Policy",
            info='Optional JSON string for the "indexing" field of the collection. '
            "See https://docs.datastax.com/en/astra-db-serverless/api-reference/collections.html#the-indexing-option",
            advanced=True,
        ),
    ]

    def del_fields(self, build_config, field_list):
        for field in field_list:
            if field in build_config:
                del build_config[field]

        return build_config

    def insert_in_dict(self, build_config, field_name, new_parameters):
        # Insert the new key-value pair after the found key
        for new_field_name, new_parameter in new_parameters.items():
            # Get all the items as a list of tuples (key, value)
            items = list(build_config.items())

            # Find the index of the key to insert after
            idx = len(items)
            for i, (key, _) in enumerate(items):
                if key == field_name:
                    idx = i + 1
                    break

            items.insert(idx, (new_field_name, new_parameter))

            # Clear the original dictionary and update with the modified items
            build_config.clear()
            build_config.update(items)

        return build_config

    def update_providers_mapping(self):
        # If we don't have token or api_endpoint, we can't fetch the list of providers
        if not self.token or not self.api_endpoint:
            self.log("Astra DB token and API endpoint are required to fetch the list of Vectorize providers.")

            return self.VECTORIZE_PROVIDERS_MAPPING

        try:
            self.log("Dynamically updating list of Vectorize providers.")

            # Get the admin object
            client = DataAPIClient(token=self.token)
            admin = client.get_admin()

            # Get the embedding providers
            db_admin = admin.get_database_admin(self.api_endpoint)
            embedding_providers = db_admin.find_embedding_providers().as_dict()

            vectorize_providers_mapping = {}

            # Map the provider display name to the provider key and models
            for provider_key, provider_data in embedding_providers["embeddingProviders"].items():
                display_name = provider_data["displayName"]
                models = [model["name"] for model in provider_data["models"]]

                vectorize_providers_mapping[display_name] = [provider_key, models]

            # Sort the resulting dictionary
            return defaultdict(list, dict(sorted(vectorize_providers_mapping.items())))
        except Exception as e:  # noqa: BLE001
            self.log(f"Error fetching Vectorize providers: {e}")

            return self.VECTORIZE_PROVIDERS_MAPPING

    def get_collection_options(self):
        client = DataAPIClient(token=self.token)

        database = client.get_database(
            self.api_endpoint,
            token=self.token,
        )

        collection = database.get_collection(self.collection_name)

        # Only get the options if the collection exists
        try:
            collection_options = collection.options()
        except CollectionNotFoundException as e:
            self.log(f"Collection not found: {e}")

            return None

        return collection_options.vector

    def update_build_config(self, build_config: dict, field_value: str, field_name: str | None = None):
        # Refresh the collection name options
        build_config["collection_name"]["options"] = self._initialize_collection_options()

        # If the collection name is set to "+ Create new collection", show the advanced options
        if field_name == "collection_name" and field_value == "+ Create new collection":
            build_config["embedding_choice"]["advanced"] = False
            build_config["embedding_choice"]["value"] = "Embedding Model"

            build_config["collection_name_new"]["advanced"] = False
            build_config["collection_name_new"]["required"] = True

            new_parameter = HandleInput(
                name="embedding_model",
                display_name="Embedding Model",
                input_types=["Embeddings"],
                info="Allows an embedding model configuration.",
            ).to_dict()

            self.insert_in_dict(build_config, "collection_name_new", {"embedding_model": new_parameter})
        elif field_name == "collection_name" and field_value != "+ Create new collection":
            build_config["collection_name_new"]["advanced"] = True
            build_config["collection_name_new"]["required"] = False
            build_config["collection_name_new"]["value"] = ""

        # Get the collection options
        collection_options = self.get_collection_options()

        # If the collection options are available, show the advanced options
        if collection_options:
            build_config["embedding_choice"]["advanced"] = True

            if collection_options.service:
                for input_field in [
                    "embedding_provider",
                    "z_01_model_parameters",
                    "z_02_api_key_name",
                    "z_03_provider_api_key",
                    "z_04_authentication",
                ]:
                    build_config[input_field]["advanced"] = False

                build_config["embedding_model"]["advanced"] = True
                build_config["embedding_provider"]["advanced"] = True
                build_config["embedding_choice"]["value"] = "Astra Vectorize"
                build_config["embedding_provider"]["value"] = collection_options.service.provider

                build_config["model"]["value"] = collection_options.service.model_name
                build_config["z_01_model_parameters"]["value"] = collection_options.service.parameters

                if collection_options.service.authentication:
                    build_config["z_02_api_key_name"]["value"] = collection_options.service.authentication.get(
                        "providerKey"
                    )
                    build_config["z_03_provider_api_key"]["value"] = collection_options.service.authentication.get(
                        "apiKey"
                    )
                build_config["z_04_authentication"]["value"] = collection_options.service.authentication
            else:
                for input_field in [
                    "z_01_model_parameters",
                    "z_02_api_key_name",
                    "z_03_provider_api_key",
                    "z_04_authentication",
                ]:
                    build_config[input_field]["advanced"] = True

                build_config["embedding_model"]["advanced"] = False
                build_config["embedding_provider"]["advanced"] = False
                build_config["embedding_choice"]["value"] = "Embedding Model"

                new_parameter = HandleInput(
                    name="embedding_model",
                    display_name="Embedding Model",
                    input_types=["Embeddings"],
                    info="Allows an embedding model configuration.",
                ).to_dict()

                self.insert_in_dict(build_config, "embedding_choice", {"embedding_model": new_parameter})

        elif field_name == "embedding_choice":
            if field_value == "Astra Vectorize":
                self.del_fields(build_config, ["embedding_model"])

                # Update the providers mapping
                vectorize_providers = self.update_providers_mapping()

                new_parameter = DropdownInput(
                    name="embedding_provider",
                    display_name="Embedding Provider",
                    options=vectorize_providers.keys(),
                    value="",
                    required=True,
                    real_time_refresh=True,
                ).to_dict()

                self.insert_in_dict(build_config, "embedding_choice", {"embedding_provider": new_parameter})
            else:
                self.del_fields(
                    build_config,
                    [
                        "embedding_provider",
                        "model",
                        "z_01_model_parameters",
                        "z_02_api_key_name",
                        "z_03_provider_api_key",
                        "z_04_authentication",
                    ],
                )

                new_parameter = HandleInput(
                    name="embedding_model",
                    display_name="Embedding Model",
                    input_types=["Embeddings"],
                    info="Allows an embedding model configuration.",
                ).to_dict()

                self.insert_in_dict(build_config, "embedding_choice", {"embedding_model": new_parameter})

        elif field_name == "embedding_provider":
            self.del_fields(
                build_config,
                ["model", "z_01_model_parameters", "z_02_api_key_name", "z_03_provider_api_key", "z_04_authentication"],
            )

            # Update the providers mapping
            vectorize_providers = self.update_providers_mapping()
            model_options = vectorize_providers[field_value][1]

            new_parameter = DropdownInput(
                name="model",
                display_name="Model",
                info="The embedding model to use for the selected provider. Each provider has a different set of "
                "models available (full list at "
                "https://docs.datastax.com/en/astra-db-serverless/databases/embedding-generation.html):\n\n"
                f"{', '.join(model_options)}",
                options=model_options,
                value=None,
                required=True,
                real_time_refresh=True,
            ).to_dict()

            self.insert_in_dict(build_config, "embedding_provider", {"model": new_parameter})

        elif field_name == "model":
            self.del_fields(
                build_config,
                ["z_01_model_parameters", "z_02_api_key_name", "z_03_provider_api_key", "z_04_authentication"],
            )

            new_parameter_1 = DictInput(
                name="z_01_model_parameters",
                display_name="Model Parameters",
                list=True,
            ).to_dict()

            new_parameter_2 = MessageTextInput(
                name="z_02_api_key_name",
                display_name="API Key Name",
                info="The name of the embeddings provider API key stored on Astra. "
                "If set, it will override the 'ProviderKey' in the authentication parameters.",
            ).to_dict()

            new_parameter_3 = SecretStrInput(
                load_from_db=False,
                name="z_03_provider_api_key",
                display_name="Provider API Key",
                info="An alternative to the Astra Authentication that passes an API key for the provider "
                "with each request to Astra DB. "
                "This may be used when Vectorize is configured for the collection, "
                "but no corresponding provider secret is stored within Astra's key management system.",
            ).to_dict()

            new_parameter_4 = DictInput(
                name="z_04_authentication",
                display_name="Authentication Parameters",
                list=True,
            ).to_dict()

            self.insert_in_dict(
                build_config,
                "model",
                {
                    "z_01_model_parameters": new_parameter_1,
                    "z_02_api_key_name": new_parameter_2,
                    "z_03_provider_api_key": new_parameter_3,
                    "z_04_authentication": new_parameter_4,
                },
            )

        return build_config

    def build_vectorize_options(self, **kwargs):
        for attribute in [
            "embedding_provider",
            "model",
            "z_01_model_parameters",
            "z_02_api_key_name",
            "z_03_provider_api_key",
            "z_04_authentication",
        ]:
            if not hasattr(self, attribute):
                setattr(self, attribute, None)

        # Fetch values from kwargs if any self.* attributes are None
        provider_mapping = self.update_providers_mapping()
        provider_value = provider_mapping.get(self.embedding_provider, [None])[0] or kwargs.get("embedding_provider")
        model_name = self.model or kwargs.get("model")
        authentication = {**(self.z_04_authentication or {}), **kwargs.get("z_04_authentication", {})}
        parameters = self.z_01_model_parameters or kwargs.get("z_01_model_parameters", {})

        # Set the API key name if provided
        api_key_name = self.z_02_api_key_name or kwargs.get("z_02_api_key_name")
        provider_key = self.z_03_provider_api_key or kwargs.get("z_03_provider_api_key")
        if api_key_name:
            authentication["providerKey"] = api_key_name
        if authentication:
            provider_key = None
            authentication["providerKey"] = authentication["providerKey"].split(".")[0]

        # Set authentication and parameters to None if no values are provided
        if not authentication:
            authentication = None
        if not parameters:
            parameters = None

        return {
            # must match astrapy.info.CollectionVectorServiceOptions
            "collection_vector_service_options": {
                "provider": provider_value,
                "modelName": model_name,
                "authentication": authentication,
                "parameters": parameters,
            },
            "collection_embedding_api_key": provider_key,
        }

    @check_cached_vector_store
    def build_vector_store(self, vectorize_options=None):
        try:
            from langchain_astradb import AstraDBVectorStore
            from langchain_astradb.utils.astradb import SetupMode
        except ImportError as e:
            msg = (
                "Could not import langchain Astra DB integration package. "
                "Please install it with `pip install langchain-astradb`."
            )
            raise ImportError(msg) from e

        try:
            if not self.setup_mode:
                self.setup_mode = self._inputs["setup_mode"].options[0]

            setup_mode_value = SetupMode[self.setup_mode.upper()]
        except KeyError as e:
            msg = f"Invalid setup mode: {self.setup_mode}"
            raise ValueError(msg) from e

        metric_value = self.metric or None
        autodetect = False

        if self.embedding_choice == "Embedding Model":
            embedding_dict = {"embedding": self.embedding_model}
        # Use autodetect if the collection name is NOT set to "+ Create new collection"
        elif self.collection_name != "+ Create new collection":
            autodetect = True
            metric_value = None
            setup_mode_value = None
            embedding_dict = {}
        else:
            from astrapy.info import CollectionVectorServiceOptions

            # Grab the collection options if available
            collection_options = self.get_collection_options()

            # Ensure collection_options and its nested attributes are handled safely
            authentication = getattr(self, "z_04_authentication", {}) or (
                collection_options.service.authentication if collection_options and collection_options.service else {}
            )

            # Build the vectorize options dictionary
            dict_options = vectorize_options or self.build_vectorize_options(
                embedding_provider=(
                    getattr(self, "embedding_provider", None)
                    or (
                        collection_options.service.provider
                        if collection_options and collection_options.service
                        else None
                    )
                ),
                model=(
                    getattr(self, "model", None)
                    or (
                        collection_options.service.model_name
                        if collection_options and collection_options.service
                        else None
                    )
                ),
                z_01_model_parameters=(
                    getattr(self, "z_01_model_parameters", None)
                    or (
                        collection_options.service.parameters
                        if collection_options and collection_options.service
                        else None
                    )
                ),
                z_02_api_key_name=(
                    getattr(self, "z_02_api_key_name", None)
                    or (authentication.get("apiKey") if authentication else None)
                ),
                z_03_provider_api_key=(
                    getattr(self, "z_03_provider_api_key", None)
                    or (authentication.get("providerKey") if authentication else None)
                ),
                z_04_authentication=authentication,
            )

            # Set the embedding dictionary
            embedding_dict = {
                "collection_vector_service_options": CollectionVectorServiceOptions.from_dict(
                    dict_options.get("collection_vector_service_options")
                ),
                "collection_embedding_api_key": dict_options.get("collection_embedding_api_key"),
            }

        try:
            vector_store = AstraDBVectorStore(
                token=self.token,
                api_endpoint=self.api_endpoint,
                namespace=self.keyspace or None,
                collection_name=getattr(self, "collection_name_new", None) or self.collection_name,
                autodetect_collection=autodetect,
                environment=(
                    parse_api_endpoint(getattr(self, "api_endpoint", None)).environment
                    if getattr(self, "api_endpoint", None)
                    else None
                ),
                metric=metric_value,
                batch_size=self.batch_size or None,
                bulk_insert_batch_concurrency=self.bulk_insert_batch_concurrency or None,
                bulk_insert_overwrite_concurrency=self.bulk_insert_overwrite_concurrency or None,
                bulk_delete_concurrency=self.bulk_delete_concurrency or None,
                setup_mode=setup_mode_value,
                pre_delete_collection=self.pre_delete_collection,
                metadata_indexing_include=[s for s in self.metadata_indexing_include if s] or None,
                metadata_indexing_exclude=[s for s in self.metadata_indexing_exclude if s] or None,
                collection_indexing_policy=orjson.dumps(self.collection_indexing_policy)
                if self.collection_indexing_policy
                else None,
                **embedding_dict,
            )
        except Exception as e:
            msg = f"Error initializing AstraDBVectorStore: {e}"
            raise ValueError(msg) from e

        self._add_documents_to_vector_store(vector_store)

        return vector_store

    def _add_documents_to_vector_store(self, vector_store) -> None:
        documents = []
        for _input in self.ingest_data or []:
            if isinstance(_input, Data):
                documents.append(_input.to_lc_document())
            else:
                msg = "Vector Store Inputs must be Data objects."
                raise TypeError(msg)

        if documents:
            self.log(f"Adding {len(documents)} documents to the Vector Store.")
            try:
                vector_store.add_documents(documents)
            except Exception as e:
                msg = f"Error adding documents to AstraDBVectorStore: {e}"
                raise ValueError(msg) from e
        else:
            self.log("No documents to add to the Vector Store.")

    def _map_search_type(self) -> str:
        if self.search_type == "Similarity with score threshold":
            return "similarity_score_threshold"
        if self.search_type == "MMR (Max Marginal Relevance)":
            return "mmr"
        return "similarity"

    def _build_search_args(self):
        query = self.search_input if isinstance(self.search_input, str) and self.search_input.strip() else None
        search_filter = (
            {k: v for k, v in self.search_filter.items() if k and v and k.strip()} if self.search_filter else None
        )

        if query:
            args = {
                "query": query,
                "search_type": self._map_search_type(),
                "k": self.number_of_results,
                "score_threshold": self.search_score_threshold,
            }
        elif self.advanced_search_filter or search_filter:
            args = {
                "n": self.number_of_results,
            }
        else:
            return {}

        filter_arg = self.advanced_search_filter or {}

        if search_filter:
            self.log(self.log(f"`search_filter` is deprecated. Use `advanced_search_filter`. Cleaned: {search_filter}"))
            filter_arg.update(search_filter)

        if filter_arg:
            args["filter"] = filter_arg

        return args

    def search_documents(self, vector_store=None) -> list[Data]:
        vector_store = vector_store or self.build_vector_store()

        self.log(f"Search input: {self.search_input}")
        self.log(f"Search type: {self.search_type}")
        self.log(f"Number of results: {self.number_of_results}")

        try:
            search_args = self._build_search_args()
        except Exception as e:
            msg = f"Error in AstraDBVectorStore._build_search_args: {e}"
            raise ValueError(msg) from e

        if not search_args:
            self.log("No search input or filters provided. Skipping search.")
            return []

        docs = []
        search_method = "search" if "query" in search_args else "metadata_search"

        try:
            self.log(f"Calling vector_store.{search_method} with args: {search_args}")
            docs = getattr(vector_store, search_method)(**search_args)
        except Exception as e:
            msg = f"Error performing {search_method} in AstraDBVectorStore: {e}"
            raise ValueError(msg) from e

        self.log(f"Retrieved documents: {len(docs)}")

        data = docs_to_data(docs)
        self.log(f"Converted documents to data: {len(data)}")
        self.status = data
        return data

    def get_retriever_kwargs(self):
        search_args = self._build_search_args()
        return {
            "search_type": self._map_search_type(),
            "search_kwargs": search_args,
        }
