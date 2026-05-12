# 新增 sensoube 接口骨架（复制用）

约定摘要见 [.cursor/rules/backend-sensoube.mdc](../../.cursor/rules/backend-sensoube.mdc)（四段式、snake_case 契约字段、模型 `*T`、路由最后一级 camelCase）。

下列示例按 **四段** 排列；若文件顶部已有 `const router = express.Router()`，则只复制对应段落。

## 1. 引用（与方法变量）

```javascript
const express = require('express');
const router = express.Router();
const Joi = require('joi');
const messageDetailT = require('../../../models/messageD');
const { validate, BaseSchema } = require('../../../utils/validate');
const { asyncHandler, sendResponse } = require('../../../utils/middleware');
```

## 2. 接口入参校验（Joi）

契约字段用 **snake_case**；schema 常量名用 **`xxxSchema`**。

```javascript
const yourActionSchema = BaseSchema.keys({
  message_list_id: Joi.string().hex().length(24).required(),
  message_detail_id_list: Joi.array()
    .items(Joi.string().hex().length(24))
    .min(1)
    .max(500)
    .unique()
    .required()
});
```

## 3. 接口通用方法（可选，仅本文件复用时放在此处）

```javascript
async function loadSomethingByListId(message_list_id) {
  // ...
}
```

## 4. 实现接口（路由注册处上方不写块注释）

路径最后一级用 **camelCase**；handler 内变量用 **snake_case**。

```javascript
router.post('/yourCamelCaseActionName', validate(yourActionSchema), asyncHandler(async (req, res) => {
  const { message_list_id, message_detail_id_list } = req.validatedData;
  const row_count = await messageDetailT.countDocuments({ messageLid: message_list_id });
  return sendResponse(res, 200, '成功', { row_count });
}));

module.exports = router;
```

在 [.ai/context/api_docs.md](../context/api_docs.md) 登记完整路径，例如 `POST /api/v3/.../yourCamelCaseActionName`。
