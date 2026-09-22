import { Prop, Schema, SchemaFactory } from '@nestjs/mongoose'
import type { HydratedDocument } from 'mongoose'

export type HeroDocument = HydratedDocument<Hero>

@Schema({ _id: false })
export class HeroName {
  @Prop({ default: '' }) first?: string
  @Prop({ default: '' }) last?: string
}
export const HeroNameSchema = SchemaFactory.createForClass(HeroName)

@Schema({ _id: false })
export class HeroDate {
  @Prop({ default: '' }) birth?: string
  @Prop({ default: '' }) dead?: string
}
export const HeroDateSchema = SchemaFactory.createForClass(HeroDate)

// The live Mongo collection stores heroes with nested fields such as:
//   name.first / name.last and date.birth / date.dead.
// Keep legacy flat fields too so older imported records remain readable.
@Schema({ collection: 'heroes', versionKey: false, strict: false })
export class Hero {
  @Prop({ type: HeroNameSchema, default: () => ({}) }) name?: HeroName
  @Prop({ type: HeroDateSchema, default: () => ({}) }) date?: HeroDate

  @Prop() id?: string
  @Prop({ default: '' }) first_name?: string
  @Prop({ default: '' }) last_name?: string
  @Prop({ default: '' }) birth_date?: string
  @Prop({ default: '' }) death_date?: string

  @Prop({ default: '' }) region?: string
  @Prop({ default: '' }) war?: string
  @Prop({ default: '' }) img_url?: string
  @Prop({ default: '' }) bio_link?: string
  @Prop({ default: '' }) bio?: string
  @Prop() created_at?: string
  @Prop() updated_at?: string
}

export const HeroSchema = SchemaFactory.createForClass(Hero)
