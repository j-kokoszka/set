#!/bin/bash
TOKEN=$(gh auth token)
git push https://x-access-token:$TOKEN@github.com/j-kokoszka/set.git feat/analytics-and-localized-exercises
