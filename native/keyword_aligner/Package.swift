// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "KeywordAligner",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "KeywordAlignerApp", targets: ["KeywordAlignerApp"]),
        .library(name: "KeywordAlignerCore", targets: ["KeywordAlignerCore"]),
        .library(name: "KeywordAlignerUI", targets: ["KeywordAlignerUI"]),
        .library(name: "KeywordAlignerBridge", type: .dynamic, targets: ["KeywordAlignerBridge"]),
    ],
    targets: [
        .target(name: "KeywordAlignerCore"),
        .target(name: "KeywordAlignerUI", dependencies: ["KeywordAlignerCore"]),
        .target(name: "KeywordAlignerBridge", dependencies: ["KeywordAlignerUI"]),
        .executableTarget(
            name: "KeywordAlignerApp",
            dependencies: ["KeywordAlignerUI"]
        ),
        .testTarget(
            name: "KeywordAlignerCoreTests",
            dependencies: ["KeywordAlignerCore"]
        ),
    ]
)
