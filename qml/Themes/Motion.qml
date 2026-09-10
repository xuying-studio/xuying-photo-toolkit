pragma Singleton

import QtQml

// 动效只改变视觉属性，不参与任何业务状态。
QtObject {
    readonly property string full: "full"
    readonly property string reduced: "reduced"
    readonly property string none: "none"

    property string policy: "full"
    readonly property int fast: policy === none ? 0 : (policy === reduced ? 100 : 140)
    readonly property int normal: policy === none ? 0 : (policy === reduced ? 140 : 220)
    readonly property int slow: policy === none ? 0 : (policy === reduced ? 180 : 280)
    readonly property int buttonPress: policy === none ? 0 : 140
    readonly property int buttonRelease: policy === none ? 0 : 100
    readonly property int pageTransition: policy === none ? 0 :
                                                   (policy === reduced ? 100 : 180)
    readonly property int toastEnter: policy === none ? 0 :
                                              (policy === reduced ? 100 : 180)
    readonly property int toastExit: policy === none ? 0 :
                                             (policy === reduced ? 100 : 140)
    readonly property int reorder: policy === none ? 0 :
                                           (policy === reduced ? 100 : 140)

    function setPolicy(requestedPolicy) {
        if ([full, reduced, none].indexOf(requestedPolicy) >= 0)
            policy = requestedPolicy
        else
            policy = reduced
    }
}
