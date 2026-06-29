from hanflow.persistence.base import Store


def test_store_is_protocol():
    # Store is a runtime_checkable Protocol; any class with the right methods matches.
    class FakeStore:
        async def save(self, key, value, **meta):
            pass

        async def load(self, key):
            return None

        async def list(self, **filters):
            return []

        async def delete(self, key):
            return True

        async def health(self):
            return True

    assert isinstance(FakeStore(), Store)
