// PreviewProvider.swift - the Space bar preview of an APlot graph.
//
// Pressing the Space bar on an .aplt file in the Finder (or choosing Quick
// Look from its menu) shows the picture APlot stored in the file.  This is
// a "data based" preview (macOS 12 and later): the extension hands Quick
// Look the PNG, and Quick Look draws, scales and zooms it by itself.

import Foundation
import CoreGraphics
import QuickLookUI
import UniformTypeIdentifiers

@objc(APlotPreviewProvider)
final class PreviewProvider: QLPreviewProvider, QLPreviewingController {

    func providePreview(for request: QLFilePreviewRequest) async throws -> QLPreviewReply {
        let png = try APlotArchive.thumbnailData(at: request.fileURL)
        let image = try APlotArchive.image(from: png)
        // APlot draws the picture for a Retina screen: two pixels to a point
        let size = CGSize(width: max(1, image.width / 2), height: max(1, image.height / 2))
        return QLPreviewReply(dataOfContentType: .png, contentSize: size) { _ in png }
    }
}
