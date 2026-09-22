import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose'
import type { HydratedDocument } from 'mongoose'

export type EventReminderDocument = HydratedDocument<EventReminder>
export type ReminderDeliveryDocument = HydratedDocument<ReminderDelivery>

@Schema({ collection: 'event_reminders', versionKey: false })
export class EventReminder {
  @Prop({ required: true, index: true }) user_id!: string
  @Prop({ required: true, index: true }) event_id!: string
  @Prop({ default: '' }) event_title!: string
  @Prop({ default: 1 }) offset_days!: number
  @Prop({ default: true, index: true }) enabled!: boolean
  @Prop({ default: 'active', index: true }) status!: string
  @Prop({ default: '' }) next_occurrence!: string
  @Prop({ default: '', index: true }) next_send_date!: string
  @Prop({ default: '' }) last_sent_occurrence!: string
  @Prop({ default: 0 }) sent_count!: number
  @Prop({ default: '' }) last_sent_at!: string
  @Prop({ default: '' }) last_error!: string
  @Prop({ default: 0 }) attempts!: number
  @Prop({ default: '' }) last_attempt_at!: string
  @Prop({ default: null, type: Date, index: true }) processing_until!: Date | null
  @Prop({ required: true }) created_at!: string
  @Prop({ required: true }) updated_at!: string
}

export const EventReminderSchema = SchemaFactory.createForClass(EventReminder)
EventReminderSchema.index({ user_id: 1, event_id: 1 }, { unique: true })
EventReminderSchema.index({ enabled: 1, status: 1, next_send_date: 1 })

@Schema({ collection: 'reminder_deliveries', versionKey: false })
export class ReminderDelivery {
  @Prop({ required: true, index: true }) reminder_id!: string
  @Prop({ required: true, index: true }) user_id!: string
  @Prop({ required: true, index: true }) event_id!: string
  @Prop({ default: '' }) event_title!: string
  @Prop({ default: '' }) occurrence!: string
  @Prop({ required: true, index: true }) status!: string
  @Prop({ default: '' }) error!: string
  @Prop({ required: true, index: true }) created_at!: string
}

export const ReminderDeliverySchema = SchemaFactory.createForClass(ReminderDelivery)
ReminderDeliverySchema.index({ created_at: -1 })
