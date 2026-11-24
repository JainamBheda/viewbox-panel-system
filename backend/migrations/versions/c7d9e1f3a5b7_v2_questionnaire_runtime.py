"""v2 questionnaire runtime

Revision ID: c7d9e1f3a5b7
Revises: 756a4a3af8c6
Create Date: 2026-11-24 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c7d9e1f3a5b7'
down_revision = '756a4a3af8c6'
branch_labels = None
depends_on = None

JSON_TYPE = sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        'questionnaire_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('survey_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('ast', JSON_TYPE, nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['survey_id'], ['surveys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('survey_id', 'version', name='uq_questionnaire_survey_version'),
    )
    op.create_index(op.f('ix_questionnaire_versions_survey_id'), 'questionnaire_versions', ['survey_id'], unique=False)
    op.create_index(op.f('ix_questionnaire_versions_status'), 'questionnaire_versions', ['status'], unique=False)

    op.create_table(
        'survey_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('survey_id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('answers', JSON_TYPE, nullable=False),
        sa.Column('path', JSON_TYPE, nullable=False),
        sa.Column('meta', JSON_TYPE, nullable=False),
        sa.Column('termination_reason', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['survey_id'], ['surveys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['questionnaire_versions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('survey_id', 'member_id', name='uq_survey_member_response'),
    )
    op.create_index(op.f('ix_survey_responses_member_id'), 'survey_responses', ['member_id'], unique=False)
    op.create_index(op.f('ix_survey_responses_status'), 'survey_responses', ['status'], unique=False)
    op.create_index(op.f('ix_survey_responses_survey_id'), 'survey_responses', ['survey_id'], unique=False)
    op.create_index(op.f('ix_survey_responses_version_id'), 'survey_responses', ['version_id'], unique=False)

    op.create_table(
        'survey_answers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('response_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.String(length=16), nullable=False),
        sa.Column('value', JSON_TYPE, nullable=False),
        sa.Column('answered_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['response_id'], ['survey_responses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('response_id', 'question_id', name='uq_response_question_answer'),
    )
    op.create_index(op.f('ix_survey_answers_response_id'), 'survey_answers', ['response_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_survey_answers_response_id'), table_name='survey_answers')
    op.drop_table('survey_answers')
    op.drop_index(op.f('ix_survey_responses_version_id'), table_name='survey_responses')
    op.drop_index(op.f('ix_survey_responses_survey_id'), table_name='survey_responses')
    op.drop_index(op.f('ix_survey_responses_status'), table_name='survey_responses')
    op.drop_index(op.f('ix_survey_responses_member_id'), table_name='survey_responses')
    op.drop_table('survey_responses')
    op.drop_index(op.f('ix_questionnaire_versions_status'), table_name='questionnaire_versions')
    op.drop_index(op.f('ix_questionnaire_versions_survey_id'), table_name='questionnaire_versions')
    op.drop_table('questionnaire_versions')
