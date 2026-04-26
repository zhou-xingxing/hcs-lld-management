.PHONY: lint test check help

lint:  ## 代码检查：ruff + black + mypy
	bash run_checks.sh

test:  ## 运行测试
	bash run_tests.sh

check: lint test  ## 完整门禁：lint → test

help:  ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-10s\033[0m %s\n", $$1, $$2}'
