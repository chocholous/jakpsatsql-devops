.PHONY: setup build test worktree worktree-remove sync-workspace

setup:
	bash .worktree-setup.sh

build:
	@echo "Build: verifying toolchain..."
	uv --version
	@if [ -f provision.py ]; then uv run python -m py_compile provision.py && echo "provision.py OK"; fi
	@echo "Build OK"

test:
	uv run pytest tests/ -v --ignore=tests/test_integration.py --ignore=tests/test_binary.py

sync-workspace:
	@python3 -c "\
	import json, os, sys; \
	root = os.path.abspath('..'); \
	ws_name = os.path.basename(root) + '.code-workspace'; \
	ws_path = os.path.join(root, ws_name); \
	folders = [{'path': 'main', 'name': 'main'}]; \
	wt_dir = os.path.join(root, 'worktrees'); \
	[folders.append({'path': f'worktrees/{d}', 'name': d}) for d in sorted(os.listdir(wt_dir)) if os.path.isfile(os.path.join(wt_dir, d, '.git'))] if os.path.isdir(wt_dir) else None; \
	data = {}; \
	exec('try:\n with open(ws_path) as f: data=json.load(f)\nexcept FileNotFoundError: pass\nexcept json.JSONDecodeError as e: sys.exit(f\"Invalid JSON in {ws_path}: {e}\")'); \
	data['folders'] = folders; \
	data.setdefault('settings', {'search.exclude': {'**/.git': True, '**/.venv': True, '**/node_modules': True, '**/__pycache__': True}}); \
	open(ws_path, 'w').write(json.dumps(data, indent=2) + '\n'); \
	print(f'Synced {ws_name}: {len(folders)} folders')"

worktree:
	@test -n "$(BRANCH)" || (echo "Usage: make worktree BRANCH=<name>" && exit 1)
	git worktree add ../worktrees/$(BRANCH) -b $(BRANCH)
	cd ../worktrees/$(BRANCH) && bash .worktree-setup.sh
	@$(MAKE) sync-workspace

worktree-remove:
	@test -n "$(BRANCH)" || (echo "Usage: make worktree-remove BRANCH=<name>" && exit 1)
	git worktree remove ../worktrees/$(BRANCH)
	git branch -D $(BRANCH)
	@$(MAKE) sync-workspace
