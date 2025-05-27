# Knowledge Providers

This module provides interfaces for integrating various knowledge management systems with the agent framework.

## Current Status

The knowledge provider system is under active development. Currently, only the base interface is implemented.

## Future Providers

We plan to support the following knowledge management systems:

- **Neptune**: Graph database integration
- **OpenSearch**: Full-text search and analytics
- **Pinecone**: Vector database for embeddings
- **ChromaDB**: Local embeddings database
- **Weaviate**: Vector search engine

## Contributing

If you're interested in implementing a knowledge provider, please see our [Contributing Guide](../../CONTRIBUTING.md) or open an issue to discuss your implementation.

## Interface

All knowledge providers should implement the `BaseKnowledgeProvider` interface:

```python
class BaseKnowledgeProvider:
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search the knowledge base."""
        pass
    
    async def store(self, data: Dict[str, Any]) -> str:
        """Store data in the knowledge base."""
        pass
    
    async def retrieve(self, id: str) -> Dict[str, Any]:
        """Retrieve specific item from knowledge base."""
        pass
```