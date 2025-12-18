from itertools import islice


def batch_generator(iterable, batch_size):
    """
    Yield successive batches from an iterable.

    Args:
        iterable: Any iterable (list, generator, etc.)
        batch_size (int): Number of items per batch

    Yields:
        list: A list containing up to batch_size items
    """
    it = iter(iterable)
    while True:
        batch = list(islice(it, batch_size))
        if not batch:
            break
        yield batch
