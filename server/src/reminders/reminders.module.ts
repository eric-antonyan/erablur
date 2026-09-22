import { Module } from '@nestjs/common'
import { MongooseModule } from '@nestjs/mongoose'
import { EventsModule } from '../events/events.module.js'
import { UsersModule } from '../users/users.module.js'
import { RemindersController } from './reminders.controller.js'
import { RemindersService } from './reminders.service.js'
import { EventReminder, EventReminderSchema, ReminderDelivery, ReminderDeliverySchema } from './schemas/reminder.schema.js'
import { TasksController } from './tasks.controller.js'

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: EventReminder.name, schema: EventReminderSchema },
      { name: ReminderDelivery.name, schema: ReminderDeliverySchema },
    ]),
    EventsModule,
    UsersModule,
  ],
  controllers: [RemindersController, TasksController],
  providers: [RemindersService],
  exports: [RemindersService],
})
export class RemindersModule {}
