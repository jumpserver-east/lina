<template>
  <el-row :gutter="20">
    <el-col :md="16" :sm="24">
      <ListTable :header-actions="headerActions" :table-config="tableConfig" />
    </el-col>
  </el-row>
</template>

<script>
import ListTable from '@/components/Table/ListTable'
import { OutputExpandFormatter } from '../formatters'
import { toSafeLocalDateStr } from '@/utils/common'

export default {
  name: 'SessionCommands',
  components: {
    ListTable
  },
  data() {
    return {
      tableConfig: {
        hasSelection: false,
        url: `/api/v1/terminal/commands/?session_id=${this.$route.params.id}`,
        columns: [
          'expandCol', 'index', 'input', 'face_verify', 'timestamp'
        ],
        columnsMeta: {
          expandCol: {
            type: 'expand',
            formatter: OutputExpandFormatter
          },
          index: {
            type: 'index',
            label: 'ID',
            sortable: 'custom'
          },
          input: {
            label: this.$t('sessions.command'),
            sortable: 'custom'
          },
          face_verify: {
            label: this.$t('sessions.faceVerify'),
            width: '100px',
            formatter: this.formatFaceVerify
          },
          timestamp: {
            label: this.$t('sessions.date'),
            width: '160px',
            sortable: 'custom',
            formatter: function(row) {
              return toSafeLocalDateStr(row.timestamp * 1000)
            }
          },
          actions: {
            has: false
          }
        }
      },
      headerActions: {
        hasExport: false,
        hasImport: false,
        hasRefresh: false,
        hasCreate: false,
        hasBulkDelete: false,
        hasBulkUpdate: false,
        hasLeftActions: false,
        hasSearch: false,
        hasRightActions: false
      }
    }
  },
  methods: {
    formatFaceVerify(row) {
      const faceVerify = row.face_verify
      if (!faceVerify) {
        return <span>-</span>
      }

      const isSuccess = faceVerify.is_success === undefined
        ? faceVerify.status === 'passed'
        : faceVerify.is_success
      const successLabel = isSuccess
        ? this.$t('sessions.faceVerifySuccess')
        : this.$t('sessions.faceVerifyFail')
      const tagType = isSuccess ? 'success' : 'danger'
      const message = this.getFaceVerifyMessage(faceVerify, isSuccess)
      const tag = <el-tag type={tagType} size='mini'>{successLabel}</el-tag>
      if (!message) {
        return tag
      }
      return (
        <el-tooltip content={message} placement='top' effect='dark'>
          {tag}
        </el-tooltip>
      )
    },
    getFaceVerifyMessage(faceVerify, isSuccess) {
      if (isSuccess) {
        return ''
      }
      if (faceVerify.message) {
        return faceVerify.message
      }
      const messageMapper = {
        token_failed: this.$t('sessions.faceVerifyTokenFailed'),
        camera_call_failed: this.$t('sessions.faceVerifyCameraCallFailed'),
        timeout: this.$t('sessions.faceVerifyTimeout'),
        failed: this.$t('sessions.faceVerifyCompareRejected'),
        error: this.$t('sessions.faceVerifyCompareError')
      }
      return messageMapper[faceVerify.status] || this.$t('sessions.faceVerifyCompareError')
    }
  }
}
</script>

<style scoped>
</style>
