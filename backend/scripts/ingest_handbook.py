"""Explicitly index the configured insurance handbook into the persistent Chroma store."""
from app.config import settings
from app.handbook_embeddings import OpenRouterEmbedder
from app.handbook_knowledge import ChromaHandbookVectorStore, load_handbook_chunks


def main() -> None:
    chunks = load_handbook_chunks(settings.HANDBOOK_SOURCE_PATH)
    embeddings = OpenRouterEmbedder().embed([chunk.content for chunk in chunks])
    ChromaHandbookVectorStore(settings.HANDBOOK_VECTOR_DB_DIR, settings.HANDBOOK_VECTOR_COLLECTION).upsert(chunks, embeddings)
    print(f"Indexed {len(chunks)} handbook chunks in {settings.HANDBOOK_VECTOR_DB_DIR}")


if __name__ == "__main__":
    main()
