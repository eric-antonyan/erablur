import { Module } from '@nestjs/common'
import { MongooseModule } from '@nestjs/mongoose'
import { EventsController } from './events.controller.js'
import { EventsService } from './events.service.js'
import { MemorialEvent, MemorialEventSchema } from './schemas/event.schema.js'

@Module({
  imports: [MongooseModule.forFeature([{ name: MemorialEvent.name, schema: MemorialEventSchema }])],
  controllers: [EventsController],
  providers: [EventsService],
  exports: [EventsService],
})
export class EventsModule {}
