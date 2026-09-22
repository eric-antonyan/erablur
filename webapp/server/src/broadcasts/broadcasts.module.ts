import { Module } from '@nestjs/common'
import { BroadcastsService } from './broadcasts.service.js'

@Module({ providers: [BroadcastsService], exports: [BroadcastsService] })
export class BroadcastsModule {}
