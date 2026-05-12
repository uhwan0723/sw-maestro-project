package com.soma2026.tikitalka.data.local

import com.soma2026.tikitalka.domain.repository.DeviceIdRepository
import platform.UIKit.UIDevice

class IosDeviceIdRepository : DeviceIdRepository {

    override suspend fun getDeviceId(): String =
        UIDevice.currentDevice.identifierForVendor?.UUIDString
            ?: platform.Foundation.NSUUID().UUIDString
}