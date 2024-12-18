from typing import Union

from django.db.models import Q
from django.db.models.signals import post_delete, post_init, post_save

from apps.celery import app
from apps.content import ComparisonOperator, CategoryName
from apps.content.models import Article, ContentRule, UserArticle
from apps.questionnaire.models import UserQuestionnaire
from apps.users.models import User


def _construct_next_query(rule: ContentRule, user_questionnaire_value: Union[str, bool]) -> Q:
    if rule.comparison_operator == ComparisonOperator.IS_EQUAL_TO.value:
        query = Q(**{rule.user_questionnaire_variable.lower(): user_questionnaire_value})

    if rule.comparison_operator == ComparisonOperator.IS_LESS_THAN.value:
        query = Q(**{f"{rule.user_questionnaire_variable.lower()}__lt": user_questionnaire_value})

    if rule.comparison_operator == ComparisonOperator.IS_GREATER_THAN.value:
        query = Q(**{f"{rule.user_questionnaire_variable.lower()}__gt": user_questionnaire_value})
    return query


@app.task
def create_user_article_relationship(article_id: int):
    """
    This function creates relationships between Users and Articles. From a set of article's rules it
    filters the user questionnaires whose users should be connected to article through the intermediary UserArticle
    model.

    The rule queryset is ordered by user questionnaire variables used in rules.
    The queries for two or more rules using the same user questionnaire variable are combined with an OR.

    When the rule user questionnaire variable changes, the previously combined query is applied using filter.
    Then the next query for another user questionnaire variable in line starts being combined.

    Following the above logic, the queries for the rules with the same variables are combined with OR. When the field
    changes, the next query will be applied with an AND.
    """
    filtered_questionnaires = UserQuestionnaire.objects.all()
    query = Q()

    # The used_user_questionnaire_variable below is used in the loop to check whether a specific rule has the same
    # field name as the previous one
    used_user_questionnaire_variable = None
    article = Article.objects.get(id=article_id)
    for rule in article.rules.order_by("user_questionnaire_variable"):
        # Here we loop though the rules ordered by field name. We combine queries from several rules with the same
        # field name with "OR" and once the field name changes, we apply the query.
        # Hence the example final queryset will be retrieved like this:
        # UserQuestionnaire.objects.filter(query1).filter(query2).filter(query3).filter(query4)...
        # and each time a new filter() is applied it results in and AND operation (with OR inside the particular query,
        # if there is more than one rule for same field name).

        next_query = _construct_next_query(rule, rule.value)
        if not used_user_questionnaire_variable or used_user_questionnaire_variable == rule.user_questionnaire_variable:
            query = query | next_query
        else:
            filtered_questionnaires = filtered_questionnaires.filter(query)
            query = next_query
        used_user_questionnaire_variable = rule.user_questionnaire_variable

    # The line below applies the last constructed query in the loop (doesn't matter if it is formed from
    # one or more rules), because, the loop is always one step behind the query - it is applying the query
    # constructed in previous loop, therefore missing the last query
    user_ids = filtered_questionnaires.filter(query).select_related("user").values_list("user", flat=True)

    # The below deletion is needed in case a new rule is added to the existing article.
    # In that case the related user set for the article will be recalculated, and some of the
    # intermediary connections (UserArticle instances) should be removed,
    # otherwise the article will be shown to the wrong users.
    UserArticle.objects.filter(article=article).exclude(user__in=user_ids).delete()

    user_article_objects = [UserArticle(article=article, user_id=user_id) for user_id in user_ids]  # type: ignore
    UserArticle.objects.bulk_create(user_article_objects, ignore_conflicts=True)


def create_user_article_relationship_when_rule_is_saved_or_deleted(sender, instance, **kwargs):
    """
    Every time a rule is created or updated we need to recalculate the set of article users and create
    corresponding relations or delete unnecessary ones
    """
    article = instance.article
    if article.is_published:
        create_user_article_relationship.delay(article.id)


def create_user_article_relationship_when_article_is_created_or_updated(sender, instance, created, **kwargs):
    """
    When a published core program article is created, there are yet no rules attached to it, therefore,
    all users should be able to access it and we create relationships between all users and the article.

    When a core program article is updated, user article relationships for the
    article are reassessed only if the article's `is_published` state changed and changed to True.
    """
    if (
        instance.category.name == CategoryName.CORE_PROGRAM.value
        or instance.category.name == CategoryName.INITIAL.value
    ):
        if created and instance.is_published:
            user_article_objects = [UserArticle(article=instance, user=user) for user in User.objects.all()]
            UserArticle.objects.bulk_create(user_article_objects, ignore_conflicts=True)
        elif instance.is_published and instance.is_published != instance.previous_is_published_state:
            create_user_article_relationship.delay(instance.id)
        instance.previous_is_published_state = instance.is_published


def create_user_article_relationships_when_user_questionnaire_is_saved(sender, instance, **kwargs):
    create_user_article_relationships_when_user_questionnaire_is_saved_task.delay(user_id=instance.user_id)


@app.task
def create_user_article_relationships_when_user_questionnaire_is_saved_task(
    user_id: int,
):
    """
    Every time user's questionnaire is created or updated, we need to reassess all core program's
    user article (published) relations to include this user, but only for the articles that have rules.

    For all the articles with no rules we just create a user article relationship for the user whose
    questionnaire is being saved
    """
    all_published_articles = Article.objects.filter(
        category__name=CategoryName.CORE_PROGRAM.value, is_published=True
    ).prefetch_related("rules")
    for article in all_published_articles:
        if article.rules.all():
            create_user_article_relationship.delay(article.id)
        else:
            UserArticle.objects.get_or_create(article=article, user_id=user_id)


post_init.connect(Article.remember_is_published_state, sender=Article)
post_save.connect(create_user_article_relationship_when_article_is_created_or_updated, sender=Article)

post_save.connect(create_user_article_relationship_when_rule_is_saved_or_deleted, sender=ContentRule)
post_delete.connect(create_user_article_relationship_when_rule_is_saved_or_deleted, sender=ContentRule)

post_save.connect(
    create_user_article_relationships_when_user_questionnaire_is_saved,
    sender=UserQuestionnaire,
)
