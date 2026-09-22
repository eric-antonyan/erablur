import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose'
import type { HydratedDocument } from 'mongoose'

export type MemorialEventDocument = HydratedDocument<MemorialEvent>

@Schema({ collection: 'events', versionKey: false, timestamps: true })
export class MemorialEvent {
  @Prop({ required: true, trim: true }) title!: string
  @Prop({ required: true, trim: true, index: true }) date!: string
  @Prop({ default: true }) annual!: boolean
  @Prop({ default: 'history', trim: true }) category!: string
  @Prop({ default: '', trim: true }) description!: string
  @Prop({ default: '', trim: true }) image_url!: string
  @Prop({ default: '', trim: true }) hero_id!: string
  @Prop({ default: '', trim: true }) source_url!: string
  @Prop({ default: true, index: true }) published!: boolean
}

export const MemorialEventSchema = SchemaFactory.createForClass(MemorialEvent)
MemorialEventSchema.index({ published: 1, date: 1 })
