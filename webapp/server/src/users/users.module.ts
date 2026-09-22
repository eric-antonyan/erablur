import { Module } from '@nestjs/common'
import { MongooseModule } from '@nestjs/mongoose'
import { TelegramAuthGuard } from '../auth/telegram-auth.js'
import { AdminAudit, AdminAuditSchema, SearchHistory, SearchHistorySchema, User, UserSchema } from './schemas/user.schema.js'
import { UsersController } from './users.controller.js'
import { UsersService } from './users.service.js'

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: User.name, schema: UserSchema },
      { name: SearchHistory.name, schema: SearchHistorySchema },
      { name: AdminAudit.name, schema: AdminAuditSchema },
    ]),
  ],
  controllers: [UsersController],
  providers: [UsersService, TelegramAuthGuard],
  exports: [UsersService, MongooseModule],
})
export class UsersModule {}
