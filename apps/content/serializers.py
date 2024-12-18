from rest_framework import serializers

from apps.content.models import Article, Category, Period, SubCategory


class ArticleSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    headline = serializers.SerializerMethodField()
    sub_headline = serializers.SerializerMethodField()
    main_text = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()
    article_image = serializers.SerializerMethodField()

    def get_title(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].title
        return obj.name

    def get_subtitle(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].subtitle
        return obj.name

    def get_headline(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].headline
        return ""

    def get_sub_headline(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].sub_headline
        return ""

    def get_main_text(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].main_text
        return ""

    def get_description(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].description
        return ""

    def get_thumbnail(self, obj):
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                domain = request.get_host()
                url = f'https://{domain}{obj.thumbnail.url}'
                return url
        return None

    def get_article_image(self, obj):
        if obj.article_image:
            request = self.context.get('request')
            if request:
                domain = request.get_host()
                url = f'https://{domain}{obj.article_image.url}'
                return url
        return None

    def get_is_read(self, obj):
        return obj.user_article[0].is_read if obj.user_article else False

    class Meta:
        model = Article
        fields = [
            "id",
            "created_at",
            "name",
            "title",
            "subtitle",
            "headline",
            "sub_headline",
            "main_text",
            "description",
            "is_read",
            "content_type",
            "thumbnail",
            "article_image",
            "video",
            "video_url",
            "category",
            "subcategory",
            "period",
            "ordering",
            "is_published",
            "lifestyle_category",
        ]


class CategorySerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    def get_title(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].title
        return obj.name

    def get_description(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].description
        return ""

    class Meta:
        model = Category
        fields = "__all__"


class CategoryDetailSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    subcategories = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    def get_title(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].title
        return obj.name
    def get_description(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].description
        return ""
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                domain = request.get_host()
                url = f'https://{domain}{obj.image.url}'
                return url
        return None
    def get_subcategories(self, obj):
        subcategories = obj.subcategories.all()
        return SubCategorySerializer(subcategories, many=True, context=self.context).data
    class Meta:
        model = Category
        fields = ['id', 'name', 'image', 'title', 'description', 'subcategories']


class SubCategorySerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    subcategories_count = serializers.SerializerMethodField()
    articles_count = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def get_title(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].title
        return obj.name

    def get_description(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].description
        return ""

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                domain = request.get_host()
                url = f'https://{domain}{obj.image.url}'
                return url
        return None

    def get_subcategories_count(self, obj):
        return obj.subCategories.count()

    def get_articles_count(self, obj):
        return obj.articles.filter(is_published=True).count()

    class Meta:
        model = SubCategory
        fields = ['id', 'category', 'parent', 'name', 'image', 'title', 'description', 'subcategories_count', 'articles_count']

class SubCategoryDetailSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    subCategories = serializers.SerializerMethodField()
    articles = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def get_title(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].title
        return obj.name

    def get_description(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].description
        return ""

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                domain = request.get_host()
                url = f'https://{domain}{obj.image.url}'
                return url
        return None

    def get_subCategories(self, obj):
        children = obj.subCategories.all()
        serializer = SubCategorySerializer(children, many=True, context=self.context)
        return serializer.data

    def get_articles(self, obj):
        articles = obj.articles.filter(is_published=True)
        return ArticleSerializer(articles, many=True, context=self.context).data

    class Meta:
        model = SubCategory
        fields = ['id', 'category', 'parent', 'name', 'image', 'title', 'description', 'subCategories', 'articles']


class PeriodSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()
    articles = ArticleSerializer(source="user_articles", many=True)

    def get_title(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].title
        return obj.name

    def get_subtitle(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].subtitle
        return ""

    def get_description(self, obj):
        if getattr(obj, "user_translations", None):
            return obj.user_translations[0].description
        return ""

    def get_is_locked(self, obj):
        intro_user_article = self.context["intro_user_article"]
        return obj.is_locked(intro_user_article)

    class Meta:
        model = Period
        exclude = ("unlocks_after_week",)


class PeriodSerializerOld(PeriodSerializer):
    def get_is_locked(self, obj):
        return obj.is_locked_old(self.context["request"].user)

    class Meta:
        model = Period
        exclude = ("unlocks_after_week",)
