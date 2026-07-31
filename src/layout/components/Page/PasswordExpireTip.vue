<template>
  <el-alert v-if="expireMsg" type="error">
    {{ expireMsg }}
  </el-alert>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'PasswordExpireTip',
  data() {
    return {
      loading: true,
      securityData: {}
    }
  },
  computed: {
    ...mapGetters(['publicSettings', 'currentUser']),
    expireMsg() {
      // 用户来源不是Local时不显示密码过期提示
      if (this.currentUser.source.value !== 'local') {
        return false
      }
      const intervalTime = this.getIntervalDays(this.currentUser.date_password_last_updated)
      const securityPasswordExpirationTime = this.publicSettings.SECURITY_PASSWORD_EXPIRATION_TIME
      if (intervalTime >= securityPasswordExpirationTime) {
        return this.$t('PasswordExpired')
      }
      if (securityPasswordExpirationTime - intervalTime <= 5) {
        return (
          this.$t('PasswordWillExpiredPrefixMsg') +
          ' ' +
          (securityPasswordExpirationTime - intervalTime) +
          ' ' +
          this.$t('PasswordWillExpiredSuffixMsg')
        )
      }
      return false
    }
  },
  methods: {
    getIntervalDays(date) {
      date = new Date(date)
      const dateExpired = this.$dayjs(date, 'YYYY-MM-DD').format('YYYY-MM-DD')
      const dateNow = this.$dayjs(new Date()).format('YYYY-MM-DD')
      return this.$dayjs(dateNow).diff(this.$dayjs(dateExpired), 'days')
    }
  }
}
</script>

<style scoped></style>
