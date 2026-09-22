import { Module } from '@nestjs/common'
import { HeroesModule } from '../heroes/heroes.module.js'
import { MetaController } from './meta.controller.js'

@Module({ imports: [HeroesModule], controllers: [MetaController] })
export class MetaModule {}
