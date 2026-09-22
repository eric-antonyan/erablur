import { Module } from '@nestjs/common'
import { MongooseModule } from '@nestjs/mongoose'
import { Hero, HeroSchema } from './schemas/hero.schema.js'
import { HeroesController } from './heroes.controller.js'
import { HeroesService } from './heroes.service.js'

@Module({
  imports: [MongooseModule.forFeature([{ name: Hero.name, schema: HeroSchema }])],
  controllers: [HeroesController],
  providers: [HeroesService],
  exports: [HeroesService],
})
export class HeroesModule {}
