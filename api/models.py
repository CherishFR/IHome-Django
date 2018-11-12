from django.db import models

# Create your models here.


class ih_user_profile(models.Model):
    up_user_id = models.AutoField("用户ID", null=False, primary_key=True)
    up_name = models.CharField("昵称", max_length=32, null=False, unique=True)
    up_mobile = models.CharField("手机号", max_length=11, null=False, unique=True)
    up_passwd = models.CharField("密码", max_length=64, null=False)
    up_real_name = models.CharField("真实姓名", max_length=32, null=True)
    up_id_card = models.CharField("身份证号", max_length=20, null=True)
    up_avatar = models.CharField("用户头像", max_length=128, null=True)
    up_admin = models.BooleanField("是否是管理员，0-不是，1-是", null=False, default='0')
    up_utime = models.DateTimeField("最后更新时间", null=False, auto_now_add=True)
    up_ctime = models.DateTimeField("创建时间", null=False, auto_now=True)

    class Meta:
        verbose_name = ("用户信息表")


class ih_user_token(models.Model):
    up_user = models.OneToOneField(to='ih_user_profile', on_delete=models.CASCADE)
    up_token = models.CharField(max_length=64)

    class Meta:
        verbose_name = ("Token表")


class ih_area_info(models.Model):
    ai_area_id = models.AutoField("区域ID", null=False, primary_key=True)
    ai_name = models.CharField("区域名称", max_length=32, null=False)
    ai_ctime = models.DateTimeField("创建时间", null=False, auto_now=True)

    class Meta:
        verbose_name = ("房源区域表")


class ih_house_info(models.Model):
    hi_house_id = models.AutoField("房屋ID", null=False, primary_key=True)
    hi_user_id = models.ForeignKey(ih_user_profile, on_delete=models.CASCADE)
    hi_title = models.CharField("房屋名称", max_length=64, null=False)
    hi_price = models.IntegerField("房屋价格，单位分", default='0', null=False)
    hi_area_id = models.ForeignKey(ih_area_info, on_delete=models.CASCADE)
    hi_address = models.CharField("地址", max_length=512, default="", null=False)
    hi_room_count = models.IntegerField("房间数", default="1", null=False)
    hi_acreage = models.IntegerField("房屋面积", default="0", null=False)
    hi_house_unit = models.CharField("房屋户型", max_length=32, default="", null=False)
    hi_capacity = models.IntegerField("容纳人数", default="1", null=False)
    hi_beds = models.CharField("床的配置", max_length=64, default="", null=False)
    hi_deposit = models.IntegerField("押金，单位分", default="0", null=False)
    hi_min_days = models.IntegerField("最短入住时间", default="1", null=False)
    hi_max_days = models.IntegerField("最长入住时间，0-不限制", default="0", null=False)
    hi_order_count = models.IntegerField("下单数量", default="0", null=False)
    hi_verify_status = models.IntegerField("审核状态，0-待审核，1-审核未通过，2-审核通过", default="0", null=False, db_index=True)
    hi_online_status = models.IntegerField("0-下线，1-上线", default="1", null=False, db_index=True)
    hi_index_image_url = models.CharField("房屋主图片url", max_length=256, null=True)
    hi_utime = models.DateTimeField("最后更新时间", null=False, auto_now_add=True)
    hi_ctime = models.DateTimeField("创建时间", null=False, auto_now=True)

    class Meta:
        verbose_name = ("房屋信息表")


class ih_house_facility(models.Model):
    hf_id = models.AutoField("自增ID", null=False, primary_key=True)
    hf_house_id = models.ForeignKey(ih_house_info, on_delete=models.CASCADE)
    hf_facility_id = models.IntegerField("房屋设施", null=False)
    hf_ctime = models.DateTimeField("创建时间", null=False, auto_now=True)

    class Meta:
        verbose_name = ("房屋设施表")


class ih_facility_catelog(models.Model):
    fc_id = models.AutoField("自增ID", null=False, primary_key=True)
    fc_name = models.CharField("设施名称", max_length=32, null=False)
    fc_ctime = models.DateTimeField("创建时间", null=False, auto_now=True)

    class Meta:
        verbose_name = ("设施型录表")


class ih_order_info(models.Model):
    oi_order_id = models.AutoField("订单ID", null=False, primary_key=True)
    oi_user_id = models.ForeignKey(ih_user_profile, on_delete=models.CASCADE)
    oi_house_id = models.ForeignKey(ih_house_info, on_delete=models.CASCADE)
    oi_begin_date = models.DateField("入住时间", null=False)
    oi_end_date = models.DateField("离开时间", null=False)
    oi_days = models.IntegerField("入住天数", null=False)
    oi_house_price = models.IntegerField("房屋单价，单位分", null=False)
    oi_amount = models.IntegerField("订单金额，单位分", null=False)
    oi_status = models.IntegerField("订单状态，0-待接单，1-待支付，2-已支付，3-待评价，4-已完成，5-已取消，6-拒接单", default="0", null=False, db_index=True)
    oi_comment = models.TextField("订单评论", null=True)
    oi_utime = models.DateTimeField("最后更新时间", null=False, auto_now_add=True)
    oi_ctime = models.DateTimeField("创建时间", null=False, auto_now=True)

    class Meta:
        verbose_name = ("订单表")


class ih_house_image(models.Model):
    hi_image_id = models.AutoField("图片ID", null=False, primary_key=True)
    hi_house_id = models.ForeignKey(ih_house_info, on_delete=models.CASCADE)
    hi_url = models.CharField("图片url", max_length=256, null=False)
    hi_ctime = models.DateTimeField("创建时间", null=False, auto_now=True)

    class Meta:
        verbose_name = ("房屋图片表")