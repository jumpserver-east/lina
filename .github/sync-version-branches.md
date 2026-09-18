# 同步上游版本及开发分支

工作流位于 `.github/workflows/sync-version-branches.yml`，只在
`jumpserver-east/lina` 的默认分支 `docker-build` 上执行。源仓库为
`https://github.com/jumpserver/lina.git`，脚本只读取源仓库，并只向当前 fork 的
`origin` 推送。

## 同步规则

- 周一至周五北京时间 09:00 自动执行实际同步，也可手动运行；手动运行默认是 dry-run。
- `dev`、`v3`、`v4`、`v5` 精确镜像 upstream，必要时使用带 lease 的强制更新。
- `vX.Y.Z`、`vX.Y.Z-lts`、`vX.Y.Z-N-lts` 版本分支只创建或 fast-forward。
- 不删除 fork 独有分支，不同步 tag，不向 upstream 写入。
- 推送凭据优先使用 `SYNC_BRANCHES_TOKEN`，否则使用 `GITHUB_TOKEN`。

## 二开分支公约

- 上游标准分支（`dev`、`v3`、`v4`、`v5` 及 `vX.Y.Z*` 版本分支）只用于同步，
  不触发 Web 镜像构建。
- 客户二开分支使用 `客户名称@基于分支名称`，例如
  `ferror@v4.10.19-lts`。客户名称使用稳定、可读的字母、数字、`.`、`_` 或 `-`，
  `@` 后必须是实际存在的基线分支。
- 涉及多个组件时，lion、koko、lina、luna 和 docker-web 使用相同的二开分支名，
  让统一 Web 构建可以在所有仓库取到同名版本。
- 不把 `docker-build` 作为应用源码分支，也不在二开分支中提交构建配置的临时改动。

## 构建逻辑

`dispatch-web-image.yml` 将 Lina 的非标准分支 push dispatch 到
`jumpserver-east/docker-web`。统一构建解析组件分支时依次尝试：

1. 与触发分支完全相同的分支名；
2. `@` 后面的基线分支（如 `v4.10.19-lts`）；
3. `dev`。

触发组件使用 push 的 commit SHA 固定版本，其他组件按上述规则选择分支。标准分支
以及 `docker-build`、`main`、`master` 的 push 被入口和 job 条件双重过滤；手动
`workflow_dispatch` 才能显式构建标准分支。

## 工作流与 Web 构建策略

`docker-build` 只保留 `jumpserver-east` 自有的：

- `dispatch-web-image.yml`
- `sync-version-branches.yml`

从 upstream 继承的 workflow 文件从 `docker-build` 删除。源码分支仍保持与 upstream
相同的提交，因此其中可能仍包含上游 workflow 文件；同步工作流通过 GitHub API 在
仓库级停用除上述白名单外、位于 `.github/workflows/` 的 YAML workflow。
GitHub 自动管理的 `Dependency Graph`（`dynamic/dependabot/update-graph`）等系统任务
不属于继承的 YAML 工作流，直接跳过；它们不支持普通 workflow 的停用 API。
停用或回读失败仍会让任务失败，日志会注明具体 workflow 路径及 ID。这个操作只作用于
`jumpserver-east/lina`，不会修改 `jumpserver/lina`。

同步创建 `dev`、所有 `v*` 开发/版本分支时不会触发 Web 镜像。创建其他分支或手动运行
时，`dispatch-web-image.yml` 继续调用
`jumpserver-east/docker-web/.github/workflows/reusable-web-dispatch.yml@docker-build`
统一构建；手动运行仍可显式选择标准分支。

## Token 权限

Fine-grained PAT 的 Resource owner 选择 `jumpserver-east`，仓库选择 `lina`，授予
**Contents: Read and write** 与 **Workflows: Read and write**，保存为仓库 Actions
secret `SYNC_BRANCHES_TOKEN`。组织策略要求审批或 SSO 时还需完成对应授权。

## 本地验证

```bash
python3 .github/scripts/test_sync_version_branches.py
python3 .github/scripts/test_workflow_policy.py
DRY_RUN=true bash .github/scripts/sync-version-branches.sh
```

## 构建邮件通知

镜像构建始终通知触发工作流的操作人，重跑时通知重跑操作人。邮件包含结果、分支/提交来源、
镜像标签和运行链接。Lina/Luna 的通知在统一 Web 构建完成后发送；dispatch 失败单独通知。
需要配置 SMTP Secrets 和私有邮箱用户映射，详见 [统一邮件配置](https://github.com/jumpserver-east/docker-web/blob/docker-build/.github/build-notifications.md)。
