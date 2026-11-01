#!/bin/sh
set -eu

has_provider_config=0
has_model=0
for arg in "$@"; do
    case "$arg" in
        --config-file | --config-file=* | --api | --api=* | --base-url | --base-url=*)
            has_provider_config=1
            ;;
        --model | --model=*)
            has_model=1
            ;;
    esac
done

if [ "$has_provider_config" -eq 0 ]; then
    if [ "$has_model" -eq 0 ]; then
        set -- --api openai --base-url https://api.openai.com/v1 --model gpt-4o "$@"
    else
        set -- --api openai --base-url https://api.openai.com/v1 "$@"
    fi
fi

exec python -m osa_tool.run "$@"
