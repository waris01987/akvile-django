from django.core.exceptions import ValidationError
from django.urls import reverse
from model_bakery.baker import make
from rest_framework import status

from apps.content import CategoryName, ComparisonOperator, UserQuestionnaireVariable
from apps.content.models import Article, Category, ContentRule, UserArticle
from apps.questionnaire import (
    Age,
    ContraceptivePill,
    FeelingToday,
    Gender,
    SkinGoal,
)
from apps.questionnaire.models import UserQuestionnaire
from apps.users.models import User
from apps.utils.tests_utils import BaseTestCase


class ContentRuleTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.user_2 = make(User, first_name="Second", last_name="Second_User", email="second@user.com")
        self.user_3 = make(User, first_name="Third", last_name="Third_User", email="third@user.com")
        self.user_4 = make(User, first_name="Fourth", last_name="Fourth_User", email="fourth@user.com")

        self.user_questionnaire_1 = make(
            UserQuestionnaire,
            user=self.user,
            skin_goal=SkinGoal.OVERALL_SKIN_HEALTH.value,
            feeling_today=FeelingToday.WELL.value,
            age=Age.AGE_22_26.value,
            gender=Gender.DIVERSE.value,
            contraceptive_pill="",
            menstruating_person=False,
        )
        self.user_questionnaire_2 = make(
            UserQuestionnaire,
            user=self.user_2,
            skin_goal=SkinGoal.LESS_WRINKLES.value,
            feeling_today=FeelingToday.LOVE_IT.value,
            age=Age.AGE_61_PLUS.value,
            gender=Gender.DIVERSE.value,
            contraceptive_pill=ContraceptivePill.STOPPED_BIRTH_CONTROL.value,
            menstruating_person=True,
        )
        self.user_questionnaire_3 = make(
            UserQuestionnaire,
            user=self.user_3,
            skin_goal=SkinGoal.LESS_SCARS.value,
            feeling_today=FeelingToday.MEHHH.value,
            age=Age.AGE_17_21.value,
            gender=Gender.MALE.value,
            contraceptive_pill="",
            menstruating_person=False,
        )
        self.user_questionnaire_4 = make(
            UserQuestionnaire,
            user=self.user_4,
            skin_goal=SkinGoal.LESS_PIMPLES.value,
            feeling_today=FeelingToday.BAD.value,
            age=Age.AGE_12_16.value,
            gender=Gender.FEMALE.value,
            contraceptive_pill=ContraceptivePill.ON_BIRTH_CONTROL.value,
            menstruating_person=True,
        )

        self.category = make(Category, name=CategoryName.CORE_PROGRAM.value)
        self.article = make(Article, category=self.category, is_published=True)

    def test_article_only_for_male_users(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.GENDER.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Gender.MALE.value,
        )
        self.assertEqual(self.article.users.count(), 1)
        self.assertEqual(self.article.users.all()[0], self.user_3)

    def test_article_only_for_female_users(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.GENDER.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Gender.FEMALE.value,
        )
        self.assertEqual(self.article.users.count(), 1)
        self.assertEqual(self.article.users.all()[0], self.user_4)

    def test_article_only_for_diverse_users(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.GENDER.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Gender.DIVERSE.value,
        )
        self.assertEqual(self.article.users.count(), 2)
        self.assertIn(self.user, self.article.users.all())
        self.assertIn(self.user_2, self.article.users.all())

    def test_article_only_for_menstruating_users(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.MENSTRUATING_PERSON.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=True,
        )
        self.assertEqual(self.article.users.count(), 2)
        self.assertIn(self.user_2, self.article.users.all())
        self.assertIn(self.user_4, self.article.users.all())

    def test_article_only_for_not_menstruating_users(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.MENSTRUATING_PERSON.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=False,
        )
        self.assertEqual(self.article.users.count(), 2)
        self.assertIn(self.user, self.article.users.all())
        self.assertIn(self.user_3, self.article.users.all())

    def test_article_for_users_from_one_age_group(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Age.AGE_12_16.value,
        )
        self.assertEqual(self.article.users.count(), 1)
        self.assertIn(self.user_4, self.article.users.all())

    def test_article_for_users_with_age_greater_than_provided(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_GREATER_THAN.value,
            value=Age.AGE_12_16.value,
        )
        self.assertEqual(self.article.users.count(), 3)
        self.assertIn(self.user, self.article.users.all())
        self.assertIn(self.user_2, self.article.users.all())
        self.assertIn(self.user_3, self.article.users.all())

    def test_article_for_users_with_age_less_than_provided(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_LESS_THAN.value,
            value=Age.AGE_61_PLUS.value,
        )
        self.assertEqual(self.article.users.count(), 3)
        self.assertIn(self.user, self.article.users.all())
        self.assertIn(self.user_3, self.article.users.all())
        self.assertIn(self.user_4, self.article.users.all())

    def test_article_for_users_in_age_group_and_of_particular_gender(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_LESS_THAN.value,
            value=Age.AGE_61_PLUS.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.GENDER.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Gender.DIVERSE.value,
        )
        self.assertEqual(self.article.users.count(), 1)
        self.assertIn(self.user, self.article.users.all())

    def test_article_for_users_with_skin_goal(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.SKIN_GOAL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=SkinGoal.LESS_PIMPLES.value,
        )
        self.assertEqual(self.article.users.count(), 1)
        self.assertIn(self.user_4, self.article.users.all())

    def test_article_for_users_with_two_skin_goal_rules(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.SKIN_GOAL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=SkinGoal.LESS_PIMPLES.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.SKIN_GOAL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=SkinGoal.LESS_SCARS.value,
        )
        self.assertEqual(self.article.users.count(), 2)
        self.assertIn(self.user_3, self.article.users.all())
        self.assertIn(self.user_4, self.article.users.all())

    def test_delete_two_article_rules_one_by_one(self):
        rule_1 = make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.CONTRACEPTIVE_PILL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=ContraceptivePill.STOPPED_BIRTH_CONTROL.value,
        )
        self.assertEqual(UserArticle.objects.count(), 1)
        self.assertEqual(self.article.users.count(), 1)
        self.assertIn(self.user_2, self.article.users.all())

        rule_2 = make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.CONTRACEPTIVE_PILL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=ContraceptivePill.ON_BIRTH_CONTROL.value,
        )
        self.assertEqual(UserArticle.objects.count(), 2)
        self.assertEqual(self.article.users.count(), 2)
        self.assertIn(self.user_2, self.article.users.all())
        self.assertIn(self.user_4, self.article.users.all())

        rule_1.delete()
        self.assertEqual(UserArticle.objects.count(), 1)
        self.assertEqual(self.article.users.count(), 1)
        self.assertEqual(self.article.article_users.count(), 1)
        self.assertIn(self.user_4, self.article.users.all())

        rule_2.delete()
        self.assertEqual(UserArticle.objects.count(), 4)
        self.assertEqual(self.article.article_users.count(), 4)
        self.assertEqual(self.article.users.count(), 4)

    def test_update_rule(self):
        rule = make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.GENDER.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Gender.DIVERSE.value,
        )
        self.assertEqual(self.article.users.count(), 2)
        self.assertIn(self.user, self.article.users.all())
        self.assertIn(self.user_2, self.article.users.all())
        self.assertEqual(UserArticle.objects.count(), 2)

        rule.value = Gender.MALE.value
        rule.save()
        self.assertEqual(self.article.users.count(), 1)
        self.assertIn(self.user_3, self.article.users.all())
        self.assertEqual(UserArticle.objects.count(), 1)

    def test_one_article_and_two_rules_with_is_greater_and_is_less_comparison_operators(
        self,
    ):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_LESS_THAN.value,
            value=Age.AGE_17_21.value,
        )
        content_rule_2 = ContentRule(
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_GREATER_THAN.value,
            value=Age.AGE_42_46.value,
        )
        with self.assertRaisesMessage(
            ValidationError,
            "Rule for this article's AGE variable with operator IS_GREATER_THAN or IS_EQUAL_THAN already exists",
        ):
            content_rule_2.clean()

    def test_article_for_users_with_two_skin_goal_rules_and_two_age_rules(self):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.SKIN_GOAL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=SkinGoal.LESS_PIMPLES.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.SKIN_GOAL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=SkinGoal.LESS_SCARS.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Age.AGE_12_16.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Age.AGE_17_21.value,
        )
        self.assertEqual(self.article.users.count(), 2)
        self.assertIn(self.user_3, self.article.users.all())
        self.assertIn(self.user_4, self.article.users.all())

    def test_article_for_users_with_two_skin_goal_rules_two_age_rules_and_one_gender_rule(
        self,
    ):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.SKIN_GOAL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=SkinGoal.LESS_PIMPLES.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.SKIN_GOAL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=SkinGoal.LESS_SCARS.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Age.AGE_12_16.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Age.AGE_17_21.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.GENDER.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Gender.FEMALE.value,
        )
        self.assertEqual(self.article.users.count(), 1)
        self.assertIn(self.user_4, self.article.users.all())

    def test_article_for_users_with_two_skin_goal_rules_one_age_rule_and_two_gender_rules(
        self,
    ):
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.SKIN_GOAL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=SkinGoal.LESS_PIMPLES.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.SKIN_GOAL.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=SkinGoal.OVERALL_SKIN_HEALTH.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_LESS_THAN.value,
            value=Age.AGE_32_36.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.GENDER.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Gender.DIVERSE.value,
        )
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.GENDER.value,
            comparison_operator=ComparisonOperator.IS_EQUAL_TO.value,
            value=Gender.FEMALE.value,
        )
        self.assertEqual(self.article.users.count(), 2)
        self.assertIn(self.user, self.article.users.all())
        self.assertIn(self.user_4, self.article.users.all())

    def test_create_published_core_program_article_makes_it_available_for_all_users(
        self,
    ):
        user_article_count = UserArticle.objects.filter(article=self.article).count()
        user_count = User.objects.count()
        self.assertEqual(user_article_count, user_count)

    def test_create_unpublished_core_program_article_does_not_create_user_article_relationships(
        self,
    ):
        new_unpublished_article = make(Article, category=self.category, is_published=False)
        user_article_relationships = UserArticle.objects.filter(article=new_unpublished_article).exists()
        self.assertEqual(user_article_relationships, False)

    def test_create_published_non_core_program_article_does_not_create_user_article_relationships(
        self,
    ):
        skin_school_category = make(Category, name=CategoryName.SKIN_SCHOOL.value)
        new_published_article = make(Article, category=skin_school_category, is_published=True)
        user_article_relationships = UserArticle.objects.filter(article=new_published_article).exists()
        self.assertEqual(user_article_relationships, False)

    def test_core_program_article_changes_from_unpublished_to_published(self):
        new_unpublished_article = make(Article, category=self.category)
        user_article_relationships = UserArticle.objects.filter(article=new_unpublished_article).exists()
        self.assertEqual(user_article_relationships, False)

        new_unpublished_article.is_published = True
        new_unpublished_article.save()

        user_article_relationships = UserArticle.objects.filter(article=new_unpublished_article).count()
        self.assertEqual(user_article_relationships, 4)

    def test_core_program_article_changes_in_other_fields_than_is_published_doesnt_affect_user_article_relations(
        self,
    ):
        new_unpublished_article = make(Article, category=self.category)
        user_article_relationships = UserArticle.objects.filter(article=new_unpublished_article).exists()
        self.assertEqual(user_article_relationships, False)

        new_unpublished_article.name = "New Name"
        new_unpublished_article.content_type = "TEXT"
        new_unpublished_article.ordering = "5"
        new_unpublished_article.save()

        user_article_relationships = UserArticle.objects.filter(article=new_unpublished_article).exists()
        self.assertEqual(user_article_relationships, False)

    def test_create_user_questionnaire_creates_new_user_article_relationship(self):
        user_article_count = UserArticle.objects.count()
        self.assertEqual(user_article_count, 4)

        user_5 = make(User)
        make(
            UserQuestionnaire,
            user=user_5,
            skin_goal=SkinGoal.LESS_PIMPLES.value,
            feeling_today=FeelingToday.BAD.value,
            age=Age.AGE_12_16.value,
            gender=Gender.FEMALE.value,
            contraceptive_pill=ContraceptivePill.ON_BIRTH_CONTROL.value,
            menstruating_person=True,
        )
        user_article_count = UserArticle.objects.count()
        self.assertEqual(user_article_count, 5)

    def test_user_questionnaire_relations_recreated_when_new_user_questionnaire_created_for_article_with_rules(
        self,
    ):
        user_article_count = UserArticle.objects.count()
        self.assertEqual(user_article_count, 4)
        self.assertEqual(user_article_count, self.article.users.count())
        self.assertIn(self.user, self.article.users.all())
        self.assertIn(self.user_2, self.article.users.all())
        self.assertIn(self.user_3, self.article.users.all())
        self.assertIn(self.user_4, self.article.users.all())

        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_GREATER_THAN.value,
            value=Age.AGE_17_21.value,
        )
        user_article_count = UserArticle.objects.count()
        self.assertEqual(user_article_count, 2)
        self.assertEqual(user_article_count, self.article.users.count())
        self.assertIn(self.user, self.article.users.all())
        self.assertIn(self.user_2, self.article.users.all())

        user_5 = make(User)
        make(
            UserQuestionnaire,
            user=user_5,
            skin_goal=SkinGoal.LESS_PIMPLES.value,
            feeling_today=FeelingToday.BAD.value,
            age=Age.AGE_32_36.value,
            gender=Gender.FEMALE.value,
            contraceptive_pill=ContraceptivePill.ON_BIRTH_CONTROL.value,
            menstruating_person=True,
        )
        user_article_count = UserArticle.objects.count()
        self.assertEqual(user_article_count, 3)
        self.assertEqual(user_article_count, self.article.users.count())
        self.assertIn(self.user, self.article.users.all())
        self.assertIn(self.user_2, self.article.users.all())
        self.assertIn(user_5, self.article.users.all())

    def test_creating_rule_for_article_with_category_other_than_core_program_fails(
        self,
    ):
        test_category = make(Category, name=CategoryName.SKIN_SCHOOL.value)
        test_article = make(Article, category=test_category)

        content_rule = ContentRule(
            article=test_article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_LESS_THAN.value,
            value=Age.AGE_61_PLUS.value,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Only articles with the Core Program category should have rules",
        ):
            content_rule.clean()

    def test_query_count_for_updating_a_user_questionnaire(self):
        # for this test we have 61 article - same number as currently in prod (2021 12 22)

        # query count when running _create_user_article_relationship for ALL articles without prefetch_related - 248

        # query count when running _create_user_article_relationship ONLY for articles that HAVE rules
        # && using prefetch_related for article rules - 70

        # create a rule for existing article
        make(
            ContentRule,
            article=self.article,
            user_questionnaire_variable=UserQuestionnaireVariable.AGE.value,
            comparison_operator=ComparisonOperator.IS_GREATER_THAN.value,
            value=Age.AGE_17_21.value,
        )
        # create more articles without rules
        make(Article, category=self.category, is_published=True, _quantity=60)

        self.query_limits["ANY PUT REQUEST"] = 70

        data = {"make_up": True}
        url = reverse("questionnaire-add-make-up", kwargs={"pk": self.user_questionnaire_1.id})
        response = self.put(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["make_up"], True)

        self.user_questionnaire_1.refresh_from_db()
        self.assertEqual(self.user_questionnaire_1.make_up, True)
