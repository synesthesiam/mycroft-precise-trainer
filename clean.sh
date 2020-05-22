#!/usr/bin/env bash
this_dir="$( cd "$( dirname "$0" )" && pwd )"

# Remove doit database
rm -f "${this_dir}"/doit.db*
