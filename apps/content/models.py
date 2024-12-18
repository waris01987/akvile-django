import datetime

from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q

from apps.content import (
    ArticleType,
    ComparisonOperator,
    ContentRuleValues,
    CategoryName,
    LifeStyleCategories,
    SubCategoryName,
    UserQuestionnaireVariable,
)
from apps.content.validators import validate_size
from apps.users.models import User
from apps.utils.models import BaseModel, BaseTranslationModel


class UserArticle(BaseModel):
    article = models.ForeignKey("Article", related_name="article_users", on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name="user_articles", on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["article", "user"], name="One user per article")]


class Article(BaseModel):
    name = models.CharField(help_text="Technical name.", unique=True, max_length=255)
    content_type = models.CharField(max_length=10, choices=ArticleType.get_choices())
    thumbnail = models.ImageField(upload_to="thumbnails")
    article_image = models.ImageField(upload_to="article_images", blank=True, default="")
    video = models.FileField(
        upload_to="videos",
        blank=True,
        default="",
        validators=[FileExtensionValidator(["mp4"]), validate_size],
    )
    video_url = models.URLField(blank=True, default="")
    category = models.ForeignKey("Category", related_name="articles", on_delete=models.PROTECT)
    subcategory = models.ForeignKey(
        "SubCategory",
        related_name="articles",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    period = models.ForeignKey(
        "Period",
        related_name="articles",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )
    users = models.ManyToManyField(User, through="UserArticle", related_name="articles")
    ordering = models.PositiveIntegerField(null=True)
    is_published = models.BooleanField(default=False)
    previous_is_published_state = None
    lifestyle_category = models.CharField(
        max_length=10, choices=LifeStyleCategories.get_choices(), blank=True, default=""
    )

    class Meta:
        ordering = ["ordering"]

    def __str__(self):
        return self.name

    def _check_max_four_lifestyle_articles(self):
        lifestyle_articles = Article.objects.exclude(lifestyle_category="")
        if (
            self not in lifestyle_articles
            and lifestyle_articles.count() >= settings.MAX_ARTICLES_WITH_LIFESTYLE_CATEGORY
        ):
            message = "Max 4 articles should be marked with lifestyle category"
            raise ValidationError(message)

    def _check_max_one_lifestyle_category_per_article(self):
        if Article.objects.filter(lifestyle_category=self.lifestyle_category).exclude(id=self.id).exists():
            message = f"Only one article should be marked with lifestyle category {self.lifestyle_category}"
            raise ValidationError(message)

    def _check_only_one_video_source_provided(self):
        if self.video and self.video_url:
            message = "Only one video source should be provided - either file or url"
            raise ValidationError(message)

    def _check_only_core_program_articles_have_period(self):
        if self.category.name.upper() != "CORE_PROGRAM" and self.period is not None:
            message = "Only articles with Core Program category should have period defined"
            raise ValidationError(message)

    def _check_initial_category_has_only_one_related_article(self):
        if (
            self.category.name.upper() == "INITIAL"
            and self.category.articles.count() > 0
            and self != self.category.articles.first()
        ):
            message = "Initial category can have one related article only and already has one"
            raise ValidationError(message)

    def _check_subcategory_belongs_to_category(self) -> None:
        message = None
        category_has_subcategories = self.category.subcategories.exists()

        if category_has_subcategories:
            if self.subcategory is None:
                message = f"Articles with {self.category.display_name} category should have subcategory defined"
            elif self.subcategory.category_id != self.category.id:
                message = (
                    f"{self.subcategory.display_name} subcategory doesn't belong to "
                    f"{self.category.display_name} category"
                )
        elif self.subcategory is not None:
            categories_with_subcategories = Category.objects.filter(
                subcategories__isnull=False
            ).distinct().values_list('display_name', flat=True)
            categories_display = " or ".join(categories_with_subcategories)
            message = f"Only articles with {categories_display} category should have subcategory defined"

        if message:
            raise ValidationError(message)

    def clean(self):
        self._check_only_one_video_source_provided()
        if getattr(self, "category", False):
            self._check_subcategory_belongs_to_category()
            self._check_only_core_program_articles_have_period()
            self._check_initial_category_has_only_one_related_article()
        if self.lifestyle_category:
            self._check_max_four_lifestyle_articles()
            self._check_max_one_lifestyle_category_per_article()

    @staticmethod
    def remember_is_published_state(sender, instance, **kwargs):
        instance.previous_is_published_state = instance.is_published


class ArticleTranslation(BaseTranslationModel):
    article = models.ForeignKey("Article", related_name="translations", on_delete=models.CASCADE)
    subtitle = models.TextField(blank=True)
    headline = models.TextField()
    sub_headline = RichTextField(blank=True)
    main_text = RichTextUploadingField(blank=True)
    description = models.CharField(max_length=255)

    class Meta(BaseTranslationModel.Meta):
        constraints = [models.UniqueConstraint(fields=["language", "article"], name="One language per article")]


class ContentRule(BaseModel):
    article = models.ForeignKey("Article", related_name="rules", on_delete=models.CASCADE)
    user_questionnaire_variable = models.CharField(max_length=30, choices=UserQuestionnaireVariable.get_choices())
    comparison_operator = models.CharField(max_length=30, choices=ComparisonOperator.get_choices())
    value = models.CharField(max_length=30, choices=ContentRuleValues.get_choices())

    def _check_if_is_greater_or_is_less_operators_are_used_only_with_age(self) -> None:
        """
        IS_GREATER_THAN or IS_EQUAL_THAN operators are currently used only with AGE variable
        """

        if self.user_questionnaire_variable != UserQuestionnaireVariable.AGE.value and (
            self.comparison_operator == ComparisonOperator.IS_GREATER_THAN.value
            or self.comparison_operator == ComparisonOperator.IS_LESS_THAN.value
        ):
            message = "IS_GREATER_THAN or IS_EQUAL_THAN operators are currently used only with AGE variable"
            raise ValidationError(message)

    def _check_if_there_is_only_one_greater_than_or_less_than_operator_per_variable(
        self,
    ) -> None:
        """
        Check if there are other rules for the same article with the same user_questionnaire_variable
        that use comparison operator "IS_GREATER_THAN" or "IS_EQUAL_THAN".
        Only one such comparison operator for article's user_questionnaire_variable is currently allowed.
        """

        if (
            self.comparison_operator == ComparisonOperator.IS_GREATER_THAN.value
            or self.comparison_operator == ComparisonOperator.IS_LESS_THAN.value
        ):
            query = Q(user_questionnaire_variable=self.user_questionnaire_variable) & (
                Q(comparison_operator=ComparisonOperator.IS_GREATER_THAN.value)
                | Q(comparison_operator=ComparisonOperator.IS_LESS_THAN.value)
            )
            if self.article.rules.filter(query).exists() and self != self.article.rules.filter(query).first():
                message = (
                    f"Rule for this article's {self.user_questionnaire_variable} variable "
                    f"with operator IS_GREATER_THAN or IS_EQUAL_THAN already exists"
                )
                raise ValidationError(message)

    def _check_that_only_articles_from_core_program_category_have_rules(self):
        if self.article.category.name.upper() != "CORE_PROGRAM":
            message = "Only articles with the Core Program category should have rules"
            raise ValidationError(message)

    def clean(self):
        self._check_if_is_greater_or_is_less_operators_are_used_only_with_age()
        self._check_if_there_is_only_one_greater_than_or_less_than_operator_per_variable()
        self._check_that_only_articles_from_core_program_category_have_rules()

    def __str__(self):
        return f"{self.user_questionnaire_variable} {self.comparison_operator} {self.value}"


class Category(BaseModel):
    name = models.CharField(max_length=30)
    image = models.ImageField(upload_to="category_images")

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    @property
    def display_name(self) -> str:
        return self.name


class CategoryTranslation(BaseTranslationModel):
    category = models.ForeignKey("Category", related_name="translations", on_delete=models.CASCADE)
    description = models.TextField()

    class Meta(BaseTranslationModel.Meta):
        constraints = [models.UniqueConstraint(fields=["language", "category"], name="One language per category")]


class SubCategory(BaseModel):
    category = models.ForeignKey("Category", related_name="subcategories", on_delete=models.CASCADE)
    parent = models.ForeignKey("SubCategory", related_name="subCategories", null=True, blank=True, default="", on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    image = models.ImageField(upload_to="subcategory_images")

    class Meta:
        verbose_name_plural = "Subcategories"

    def __str__(self):
        return self.name

    @property
    def display_name(self) -> str:
        return self.name


class SubCategoryTranslation(BaseTranslationModel):
    subcategory = models.ForeignKey("Subcategory", related_name="translations", on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    class Meta(BaseTranslationModel.Meta):
        constraints = [models.UniqueConstraint(fields=["language", "subcategory"], name="One language per subcategory")]


class Period(BaseModel):
    name = models.CharField(help_text="Technical name.", unique=True, max_length=255)
    image = models.ImageField(upload_to="period_images")
    period_number_image = models.ImageField(upload_to="period_number_images")
    unlocks_after_week = models.IntegerField(
        help_text="Number of a week after which the period unlocks",
        unique=True,
    )
    ordering = models.PositiveIntegerField()

    def is_locked_old(self, user: User) -> bool:
        if not user.is_questionnaire_finished:
            return True

        period_unlocks_after = datetime.timedelta(weeks=self.unlocks_after_week)
        user_questionnaire_created_at = user.questionnaire.created_at
        now = datetime.datetime.now(datetime.timezone.utc)

        return user_questionnaire_created_at + period_unlocks_after > now

    def is_locked(self, intro_user_article: UserArticle) -> bool:
        if not intro_user_article or not intro_user_article.is_read:
            return True

        period_unlocks_after = datetime.timedelta(weeks=self.unlocks_after_week)
        intro_article_read_at = intro_user_article.read_at
        now = datetime.datetime.now(datetime.timezone.utc)

        return intro_article_read_at + period_unlocks_after > now

    class Meta:
        ordering = ["ordering"]

    def __str__(self):
        return self.name


class PeriodTranslation(BaseTranslationModel):
    period = models.ForeignKey("Period", related_name="translations", on_delete=models.CASCADE)
    subtitle = models.CharField(max_length=255)
    description = models.CharField(max_length=255)

    class Meta(BaseTranslationModel.Meta):
        constraints = [models.UniqueConstraint(fields=["language", "period"], name="One language per period")]
