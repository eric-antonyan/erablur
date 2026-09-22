import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose'
import type { HydratedDocument } from 'mongoose'

export type ModerationStatus = 'active' | 'restricted' | 'blocked'
export type UserDocument = HydratedDocument<User>

@Schema({ collection: 'users', versionKey: false })
export class User {
  @Prop({ required: true, unique: true, index: true }) id!: string
  @Prop({ default: '' }) username!: string
  @Prop({ default: '' }) first_name!: string
  @Prop({ default: '' }) last_name!: string
  @Prop({ default: '' }) language_code!: string
  @Prop({ default: '' }) photo_url!: string
  @Prop({ default: 0 }) search_count!: number
  @Prop({ default: '' }) last_query!: string
  @Prop({ default: 'active', index: true }) moderation_status!: ModerationStatus
  @Prop({ default: '' }) moderation_reason!: string
  @Prop({ default: '' }) moderation_note!: string
  @Prop({ default: '' }) restricted_until!: string
  @Prop({ default: '' }) moderated_at!: string
  @Prop({ default: '' }) moderated_by!: string
  @Prop({ default: '' }) joined_at!: string
  @Prop({ default: '', index: true }) last_seen_at!: string
  @Prop({ default: '' }) updated_at!: string
}
export const UserSchema = SchemaFactory.createForClass(User)

@Schema({ collection: 'search_history', versionKey: false })
export class SearchHistory {
  @Prop({ required: true, index: true }) user_id!: string
  @Prop({ required: true }) query!: string
  @Prop({ default: '' }) hero_id!: string
  @Prop({ default: '' }) hero_name!: string
  @Prop({ required: true }) searched_at!: string
}
export type SearchHistoryDocument = HydratedDocument<SearchHistory>
export const SearchHistorySchema = SchemaFactory.createForClass(SearchHistory)

@Schema({ collection: 'admin_audit', versionKey: false })
export class AdminAudit {
  @Prop({ required: true, index: true }) action!: string
  @Prop({ required: true, index: true }) user_id!: string
  @Prop({ default: '' }) reason!: string
  @Prop({ default: '' }) note!: string
  @Prop({ default: '' }) restricted_until!: string
  @Prop({ required: true, index: true }) created_at!: string
  @Prop({ default: 'admin' }) actor!: string
}
export type AdminAuditDocument = HydratedDocument<AdminAudit>
export const AdminAuditSchema = SchemaFactory.createForClass(AdminAudit)
