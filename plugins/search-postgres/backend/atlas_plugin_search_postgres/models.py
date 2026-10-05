from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models


class SearchIndexEntry(models.Model):
    """One indexed document.

    `search_vector` is stored, not a database-generated column, because the
    text-search configuration is a plugin setting: title lexemes carry weight
    A and body lexemes weight B, so a title match outranks a body-only match.
    """

    document_id = models.CharField(max_length=512, unique=True)
    kind = models.CharField(max_length=128)
    title = models.TextField()
    body = models.TextField(blank=True, default="")
    search_vector = SearchVectorField()

    class Meta:
        indexes = (GinIndex(fields=("search_vector",), name="search_pg_vector_gin"),)
