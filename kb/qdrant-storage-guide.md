# How to Store Data in Qdrant - Complete Guide
*Generated from comprehensive Qdrant documentation research via context7*

## 📊 Qdrant Data Storage Fundamentals

### Core Concepts
Qdrant stores data as **points** consisting of:
- **ID**: Unique identifier (numeric or UUID)
- **Vector**: Array of floats representing semantic/embeddings
- **Payload**: JSON-like metadata (optional)

### Basic Storage Operations

#### 1. Create Collection
```bash
PUT /collections/test_collection
Content-Type: application/json

{
    "vectors": {
      "size": 4,
      "distance": "Dot"
    }
}
```

#### 2. Store Points with Vectors & Payload
```bash
PUT /collections/test_collection/points?wait=true
Content-Type: application/json

{
    "points": [
      {"id": 1, "vector": [0.05, 0.61, 0.76, 0.74], "payload": {"city": "Berlin"}},
      {"id": 2, "vector": [0.19, 0.81, 0.75, 0.11], "payload": {"city": ["Berlin", "London"]}},
      {"id": 3, "vector": [0.36, 0.55, 0.47, 0.94], "payload": {"city": ["Berlin", "Moscow"]}},
      {"id": 4, "vector": [0.18, 0.01, 0.85, 0.80], "payload": {"city": ["London", "Moscow"]}},
      {"id": 5, "vector": [0.24, 0.18, 0.22, 0.44], "payload": {"count": [0]}},
      {"id": 6, "vector": [0.35, 0.08, 0.11, 0.44]}
    ]
}
```

## 🗄️ Data Structures & Types

### Point Structure
```python
PointStruct:
  id: PointId (numeric or UUID)
  payload: Dict[str, Value] (JSON-like metadata)
  vectors: Vectors (dense, sparse, or named vectors)
```

### Supported Data Types
```python
Value types:
- null_value: NullValue
- number_value: float
- string_value: str
- bool_value: bool
- struct_value: Dict[str, Value] (nested objects)
- list_value: List[Value] (arrays)
```

### Vector Types
```python
Vector types:
- DenseVector: List[float]
- SparseVector: {values: List[float], indices: List[int]}
- MultiDenseVector: List[DenseVector]
- NamedVectors: Dict[str, Vector]
```

## 🏗️ Collection Management

### Create Collection with Advanced Config
```python
CollectionParams:
  shard_number: int (default: 1)
  on_disk_payload: bool (store payload on disk vs RAM)
  vectors_config: VectorsConfig
  replication_factor: int
  write_consistency_factor: int
  read_fan_out_factor: int
```

### Vector Configuration
```python
VectorParams:
  size: int (vector dimensions)
  distance: "Cosine" | "Euclid" | "Dot" | "Manhattan"
  hnsw_config: HnswConfigDiff (indexing parameters)
  quantization_config: QuantizationConfig (compression)
  on_disk: bool (store vectors on disk)
  datatype: "Float32" | "Uint8" | "Float16"
```

## 💾 Storage & Persistence

### Docker Persistence
```bash
# Mount storage volume for persistence
docker run -p 6333:6333 \
    -v $(pwd)/path/to/data:/qdrant/storage \
    -v $(pwd)/path/to/snapshots:/qdrant/snapshots \
    -v $(pwd)/path/to/custom_config.yaml:/qdrant/config/production.yaml \
    qdrant/qdrant
```

### Python Client Storage Options
```python
# In-memory (temporary)
from qdrant_client import QdrantClient
client = QdrantClient(":memory:")

# Persistent storage
client = QdrantClient(path="path/to/db")

# Remote connection
client = QdrantClient("localhost", port=6333)
```

## 🔄 CRUD Operations

### Create/Upsert Points
```python
UpsertPoints:
  collection_name: str
  wait: bool (wait for operation completion)
  points: List[PointStruct]
  ordering: WriteOrdering (optional)
  shard_key_selector: ShardKeySelector (optional)
```

### Batch Operations
```python
UpdateBatchPoints:
  collection_name: str
  wait: bool
  operations: List[PointsUpdateOperation]
  ordering: WriteOrdering
```

### Update Operations Available
- `upsert`: Insert or update points
- `delete_points`: Remove points by ID or filter
- `set_payload`: Add/update payload fields
- `overwrite_payload`: Replace entire payload
- `delete_payload`: Remove payload fields
- `update_vectors`: Modify vectors
- `delete_vectors`: Remove vectors
- `clear_payload`: Remove all payload data

## 🔍 Querying & Retrieval

### Search Points
```python
SearchPoints:
  collection_name: str (required)
  vector: List[float] (required)
  filter: Filter (optional)
  limit: int (required)
  with_payload: WithPayloadSelector (optional)
  params: SearchParams (optional)
  score_threshold: float (optional)
  offset: int (optional)
  vector_name: str (optional)
  with_vectors: WithVectorsSelector (optional)
```

### Filtering Options
```python
Filter:
  must: List[Condition] (all conditions must match)
  should: List[Condition] (at least one must match)
  must_not: List[Condition] (none must match)

Condition types:
- FieldCondition: Compare payload fields
- IsEmptyCondition: Check if field is empty
- HasIdCondition: Check for specific point IDs
- IsNullCondition: Check if field is null
- NestedCondition: Query nested objects
- HasVectorCondition: Check for vector existence
```

## ⚡ Performance & Optimization

### Indexing Configuration
```python
HnswConfigDiff:
  m: int (number of connections per node)
  ef_construct: int (construction quality)
  full_scan_threshold: int (when to use brute force)
  max_indexing_threads: int
  on_disk: bool (store index on disk)
```

### Quantization (Compression)
```python
QuantizationConfig:
  scalar: ScalarQuantization
  product: ProductQuantization
  binary: BinaryQuantization

ScalarQuantization:
  type: "int8" | "uint8"
  quantile: float
  always_ram: bool
```

### Payload Indexing
```python
PayloadIndexParams:
  keyword_index_params: KeywordIndexParams
  integer_index_params: IntegerIndexParams
  float_index_params: FloatIndexParams
  text_index_params: TextIndexParams
  bool_index_params: BoolIndexParams
  datetime_index_params: DatetimeIndexParams
```

## 🏗️ Advanced Features

### Sharding & Replication
```python
CollectionParams:
  shard_number: int (number of shards)
  replication_factor: int (replicas per shard)
  write_consistency_factor: int (consistency level)
  read_fan_out_factor: int (read distribution)
```

### Sparse Vectors
```python
SparseVector:
  values: List[float]
  indices: List[int]

SparseVectorConfig:
  index: SparseIndexConfig
  modifier: SparseVectorModifier
```

### Multi-vector Support
```python
MultiVectorConfig:
  comparator: "max_sim" | "sum"
```

## 📊 Monitoring & Usage

### Collection Information
```python
CollectionInfo:
  status: CollectionStatus
  optimizer_status: OptimizerStatus
  vectors_count: int
  segments_count: int
  config: CollectionConfig
  payload_schema: Dict[str, PayloadSchemaInfo]
  points_count: int
  indexed_vectors_count: int
```

### Usage Statistics
```python
Usage:
  hardware: HardwareUsage
  inference: InferenceUsage
```

## 🔧 Best Practices

### Data Organization
1. **Choose appropriate distance metric** based on your embeddings
2. **Configure vector size** to match your embedding dimensions
3. **Use payload indexing** for frequently filtered fields
4. **Enable quantization** for large-scale deployments
5. **Configure sharding** for distributed setups

### Performance Tuning
1. **Set HNSW parameters** based on your accuracy/speed requirements
2. **Use on-disk storage** for large datasets
3. **Enable payload indexing** for filtered searches
4. **Configure replication** for high availability
5. **Monitor collection metrics** for optimization

### Storage Management
1. **Mount volumes** for Docker persistence
2. **Configure snapshots** for backups
3. **Set appropriate shard numbers** for your scale
4. **Monitor disk usage** with on_disk_payload settings
5. **Use strict mode** for production deployments

This comprehensive guide covers all major aspects of storing and managing data in Qdrant, from basic point insertion to advanced configuration and optimization strategies.