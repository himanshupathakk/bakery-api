from marshmallow import Schema, fields, validate


# ── Tag Schemas ────────────────────────────────────────────────────────────────

class PlainTagSchema(Schema):
    id   = fields.Int(dump_only=True)
    name = fields.Str(required=True)


class TagSchema(PlainTagSchema):
    products = fields.List(fields.Nested(lambda: PlainProductSchema()), dump_only=True)


# ── Category Schemas ───────────────────────────────────────────────────────────

class PlainCategorySchema(Schema):
    id          = fields.Int(dump_only=True)
    name        = fields.Str(required=True)
    description = fields.Str(load_default=None)


class CategorySchema(PlainCategorySchema):
    products = fields.List(fields.Nested(lambda: PlainProductSchema()), dump_only=True)


# ── Product Schemas ────────────────────────────────────────────────────────────

class PlainProductSchema(Schema):
    id             = fields.Int(dump_only=True)
    name           = fields.Str(required=True)
    description    = fields.Str(load_default=None)
    price          = fields.Float(required=True)
    stock_quantity = fields.Int(load_default=0)
    is_available   = fields.Bool(load_default=True)
    image_url      = fields.Str(load_default=None)


class ProductSchema(PlainProductSchema):
    category_id = fields.Int(load_default=None)
    category    = fields.Nested(PlainCategorySchema(), dump_only=True)
    tags        = fields.List(fields.Nested(PlainTagSchema()), dump_only=True)
    reviews     = fields.List(fields.Nested(lambda: PlainReviewSchema()), dump_only=True)


class ProductUpdateSchema(Schema):
    name           = fields.Str()
    description    = fields.Str()
    price          = fields.Float()
    stock_quantity = fields.Int()
    is_available   = fields.Bool()
    category_id    = fields.Int()
    image_url      = fields.Str(allow_none=True, load_default=None)


# ── Review Schemas ─────────────────────────────────────────────────────────────

class PlainReviewSchema(Schema):
    id         = fields.Int(dump_only=True)
    rating     = fields.Int(required=True, validate=validate.Range(min=1, max=5))
    comment    = fields.Str(load_default=None)
    created_at = fields.DateTime(dump_only=True)


class ReviewSchema(PlainReviewSchema):
    user_id    = fields.Int(dump_only=True)
    product_id = fields.Int(dump_only=True)
    user       = fields.Nested(lambda: PlainUserSchema(), dump_only=True)


# ── Order Schemas ──────────────────────────────────────────────────────────────

class OrderItemSchema(Schema):
    id         = fields.Int(dump_only=True)
    product_id = fields.Int(required=True)
    quantity   = fields.Int(required=True, validate=validate.Range(min=1))
    price      = fields.Float(dump_only=True)
    product    = fields.Nested(PlainProductSchema(), dump_only=True)


class PlainOrderSchema(Schema):
    id          = fields.Int(dump_only=True)
    status      = fields.Str(dump_only=True)
    total_price = fields.Float(dump_only=True)
    note        = fields.Str(load_default=None)
    created_at  = fields.DateTime(dump_only=True)


class OrderSchema(PlainOrderSchema):
    user_id     = fields.Int(dump_only=True)
    order_items = fields.List(fields.Nested(OrderItemSchema()), dump_only=True)
    user        = fields.Nested(lambda: PlainUserSchema(), dump_only=True)


class CreateOrderSchema(Schema):
    items = fields.List(fields.Nested(OrderItemSchema(only=("product_id", "quantity"))), required=True)
    note  = fields.Str(load_default=None)


class OrderStatusSchema(Schema):
    status = fields.Str(required=True, validate=validate.OneOf(
        ["pending", "confirmed", "preparing", "ready", "delivered", "cancelled"]
    ))


# ── User Schemas ───────────────────────────────────────────────────────────────

class PlainUserSchema(Schema):
    id       = fields.Int(dump_only=True)
    username = fields.Str(dump_only=True)


class UserSchema(Schema):
    id       = fields.Int(dump_only=True)
    username = fields.Str(dump_only=True)
    email    = fields.Email(dump_only=True)
    role     = fields.Str(dump_only=True)


class UserRegisterSchema(Schema):
    id       = fields.Int(dump_only=True)
    username = fields.Str(required=True)
    email    = fields.Email(load_default=None)
    role     = fields.Str(load_default="customer")
    password = fields.Str(required=True, load_only=True)


class UserLoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class UserUpdateSchema(Schema):
    email = fields.Email()