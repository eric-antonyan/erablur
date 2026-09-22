import { Module } from '@nestjs/common'
import { EventsModule } from '../events/events.module.js'
import { BroadcastsModule } from '../broadcasts/broadcasts.module.js'
import { UsersModule } from '../users/users.module.js'
import { RemindersModule } from '../reminders/reminders.module.js'
import { AdminAuthService } from './admin-auth.service.js'
import { AdminsService } from './admins.service.js'
import { AdminController } from './admin.controller.js'

@Module({
  imports: [EventsModule, UsersModule, RemindersModule, BroadcastsModule],
  controllers: [AdminController],
  providers: [AdminAuthService, AdminsService],
  exports: [AdminAuthService, AdminsService],
})
export class AdminModule {}
