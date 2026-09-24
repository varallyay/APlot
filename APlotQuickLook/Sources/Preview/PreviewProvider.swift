// PreviewProvider.swift - the Space bar preview of an APlot graph.
//
// Pressing the Space bar on an .aplt file in the Finder (or choosing Quick
// Look from its menu) shows the picture APlot stored in the file.  This is
// a "data based" preview (macOS 12 and later): the extension hands Quick
// Look the PNG, and Quick Look draws, scales and zooms it by itself.
//
// The preview asks for a window `previewPoints` wide (along the longer
// side of the picture) - far larger than any icon.  APlot stores the
// picture 2048 pixels wide, two pixels to a point, so it is sharp on a
// Retina screen; a smaller picture of an older graph is simply enlarged.

import Foundation
import CoreGraphics
import QuickLookUI
import UniformTypeIdentifiers

@objc(APlotPreviewProvider)
final class PreviewProvider: QLPreviewProvider, QLPreviewingController {

    /// How large the preview window is asked to be, in points.
    static let previewPoints: CGFloat = 1024

    func providePreview(for request: QLFilePreviewRequest) async throws -> QLPreviewReply {
        let png = try APlotArchive.thumbnailData(at: request.fileURL)
        let image = try APlotArchive.image(from: png)
        let box = CGSize(width: Self.previewPoints, height: Self.previewPoints)
        let size = APlotArchive.fitting(CGSize(width: image.width, height: image.height),
                                        into: box)
        return QLPreviewReply(dataOfContentType: .png, contentSize: size) { _ in png }
    }
}
