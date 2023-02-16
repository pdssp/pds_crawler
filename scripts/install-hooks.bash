#!/usr/bin/env bash

GIT_DIR=$(git rev-parse --git-dir)

echo "Installing hooks..."
# this command creates symlink to our pre-commit script
ln -s ../../scripts/post-commit.bash $GIT_DIR/hooks/post-commit
echo "Done!"
