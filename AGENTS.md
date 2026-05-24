# AGENTS.md

## 需求背景

本项目需要在审计台命令记录中展示高危命令人脸核验结果。Lina 是 JumpServer 管理后台和审计台前端，负责展示命令记录、会话详情、审批详情和相关配置。

完整业务链路：

1. 运维人员在 KoKo 终端提交高危命令。
2. JumpServer 后端触发摄像头抓拍和 AI 人脸比对。
3. 人脸比对通过后进入人工审批。
4. 审批通过后命令执行。
5. 审计人员在 Lina 审计台查看命令记录，需要看到人脸比对记录。

## 组件边界

Lina 负责：

- 展示命令记录中的人脸核验状态。
- 在命令记录详情或展开行中展示比对分数、阈值、时间、关联工单。
- 如后端提供图片访问接口，可按权限展示抓拍图和人脸库图。
- 在审批详情中展示关联的人脸核验摘要。
- 增加必要 i18n 文案。

Lina 不负责：

- 解析终端命令。
- 调用拍照系统。
- 调用 AI 人脸平台。
- 保存照片。
- 决定命令是否放行。

## 涉及代码目录

主要目录：

- `src/views/sessions/CommandList/BaseList.vue`
  - 审计台命令记录列表。
  - 需要增加“人脸核验”列或展开详情。
- `src/views/sessions/SessionDetail/SessionCommands.vue`
  - 会话详情中的命令记录。
  - 需要展示该会话内命令对应的人脸核验记录。
- `src/views/tickets/CommandConfirm/Detail/TicketDetail.vue`
  - 命令复核工单详情。
  - 如后端返回人脸核验摘要，可在工单详情展示。
- `src/api/`
  - 如需要独立查询人脸核验详情，可新增 API 方法。
  - 如果 `/api/v1/terminal/commands/` 已内联返回 `face_verify`，则不需要新增 API。
- `src/i18n/langs/zh.json`
- `src/i18n/langs/en.json`
- `src/i18n/langs/zh_Hant.json`
- `src/i18n/langs/ja.json`
  - 新增文案。
- `src/router/audit/sessions.js`
  - 一般不需要改；命令记录路由已存在。
- `src/router/console/sessions.js`
  - 一般不需要改；命令记录路由已存在。

## 后端接口依赖

命令记录接口：

```text
GET /api/v1/terminal/commands/
```

期望新增字段：

```json
{
  "face_verify": {
    "sign": "a3f1ca6c-a822-460d-9f80-c9474131c4ac",
    "status": "passed",
    "score": 91.2,
    "threshold": 80,
    "ticket_id": "工单 ID",
    "date_compared": "2026-05-21T10:00:00+08:00"
  }
}
```

状态枚举建议：

```text
created
waiting_photo
photo_received
comparing
passed
failed
timeout
error
```

展示映射：

```text
passed -> 通过
failed -> 未通过
timeout -> 超时
error -> 异常
waiting_photo -> 等待拍照
photo_received -> 已收到照片
comparing -> 比对中
created -> 已创建
空值 -> 无
```

## 页面逻辑

### 1. 命令记录列表

位置：

```text
src/views/sessions/CommandList/BaseList.vue
```

建议改动：

- 在 `columns` 中新增 `face_verify`。
- 在 `columnsMeta` 中定义 formatter。
- 无人脸记录时显示 `-`。
- 通过显示绿色或普通状态。
- 失败、超时、异常显示危险色。
- 鼠标悬停或展开行显示分数、阈值、时间、关联工单。

展示内容建议：

```text
人脸核验：通过
分数：91.2
阈值：80
时间：2026-05-21 10:00:00
工单：查看
```

### 2. 会话详情命令记录

位置：

```text
src/views/sessions/SessionDetail/SessionCommands.vue
```

建议改动：

- 同样增加 `face_verify` 展示。
- 会话详情里空间较小，建议放到展开行，不一定作为固定列。

### 3. 命令复核工单详情

位置：

```text
src/views/tickets/CommandConfirm/Detail/TicketDetail.vue
```

建议改动：

- 如果后端在工单详情返回 `face_verify`，展示核验摘要。
- 不应在无权限情况下展示照片。

### 4. 图片展示

第一阶段建议只展示摘要，不展示照片。

如果必须展示照片：

- 后端提供独立详情接口。
- 前端点击“查看人脸记录”后弹窗展示。
- 图片 URL 必须有权限控制和过期机制。
- 不要把完整 Base64 放入命令列表接口，避免列表过重。

## i18n 文案建议

新增 key 可放在 `sessions` 下：

```json
{
  "faceVerify": "人脸核验",
  "faceVerifyStatus": "核验状态",
  "faceVerifyScore": "比对分数",
  "faceVerifyThreshold": "通过阈值",
  "faceVerifyTime": "比对时间",
  "faceVerifyPassed": "通过",
  "faceVerifyFailed": "未通过",
  "faceVerifyTimeout": "超时",
  "faceVerifyError": "异常",
  "faceVerifyNone": "无"
}
```

## 验收标准

- 命令记录列表能展示人脸核验状态。
- 会话详情命令记录能展示对应人脸核验摘要。
- 人脸失败、超时、异常有明显状态。
- 无人脸核验记录的普通命令不受影响。
- 列表接口不加载大体积图片 Base64。
- 无权限用户不能看到敏感照片。
