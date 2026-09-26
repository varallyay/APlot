// APlotArchive.swift - the picture inside an APlot graph (.aplt).
//
// An .aplt file is a ZIP container:
//
//     mimetype                   "application/x-aplot", stored, first
//     document.json              the data and every diagram
//     Thumbnails/thumbnail.png   a picture of the first diagram (stored)
//     Thumbnails/preview.pdf     every diagram, one page each (stored)
//
// The Quick Look extensions only need those two entries, so this file
// reads just enough of the ZIP format to find one: the directory at the
// end of the file, one entry of it, and that entry's local header.  APlot
// stores them uncompressed; an entry that some other program has
// compressed again ("deflate") is unpacked with Apple's Compression library.
// No third party code is needed.

import Foundation
import CoreGraphics
import ImageIO
import Compression

enum APlotArchiveError: Error, CustomStringConvertible {
    case notAContainer          // a plain JSON graph of an older APlot
    case noPicture              // a container without the picture
    case damaged(String)
    case unreadablePicture

    var description: String {
        switch self {
        case .notAContainer: return "not an APlot ZIP container (an older graph?)"
        case .noPicture: return "the graph carries no picture"
        case .damaged(let why): return "the container is damaged: \(why)"
        case .unreadablePicture: return "the picture cannot be read"
        }
    }
}

enum APlotArchive {
    static let thumbnailEntry = "Thumbnails/thumbnail.png"
    static let previewEntry = "Thumbnails/preview.pdf"
    /// Nothing larger is unpacked: a picture of a graph is far smaller.
    static let largestEntry = 64 << 20

    // MARK: the picture

    /// The PNG bytes of the picture stored in the graph at `url`.
    static func thumbnailData(at url: URL) throws -> Data {
        let file = try Data(contentsOf: url, options: .mappedIfSafe)
        return try entry(named: thumbnailEntry, in: file)
    }

    /// The PDF of every diagram of the graph at `url` (one page each).
    static func previewData(at url: URL) throws -> Data {
        let file = try Data(contentsOf: url, options: .mappedIfSafe)
        return try entry(named: previewEntry, in: file)
    }

    /// The size of the first page of a PDF, in points.
    static func firstPageSize(of pdf: Data) throws -> CGSize {
        guard let provider = CGDataProvider(data: pdf as CFData),
              let document = CGPDFDocument(provider),
              document.numberOfPages > 0,
              let page = document.page(at: 1) else {
            throw APlotArchiveError.unreadablePicture
        }
        let box = page.getBoxRect(.mediaBox)
        guard box.width > 0, box.height > 0 else {
            throw APlotArchiveError.unreadablePicture
        }
        return box.size
    }

    /// The picture of the graph at `url`, ready to be drawn.
    static func thumbnailImage(at url: URL) throws -> CGImage {
        return try image(from: thumbnailData(at: url))
    }

    static func image(from png: Data) throws -> CGImage {
        guard let source = CGImageSourceCreateWithData(png as CFData, nil),
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
            throw APlotArchiveError.unreadablePicture
        }
        return image
    }

    /// `size` made as large as fits into `box`, keeping its proportions.
    static func fitting(_ size: CGSize, into box: CGSize) -> CGSize {
        guard size.width > 0, size.height > 0, box.width > 0, box.height > 0 else {
            return box
        }
        let scale = min(box.width / size.width, box.height / size.height)
        return CGSize(width: (size.width * scale).rounded(.down),
                      height: (size.height * scale).rounded(.down))
    }

    // MARK: the ZIP container

    private static let endSignature = 0x0605_4b50       // "PK\u{5}\u{6}"
    private static let entrySignature = 0x0201_4b50     // "PK\u{1}\u{2}"
    private static let localSignature = 0x0403_4b50     // "PK\u{3}\u{4}"

    /// The unpacked bytes of the entry called `name`.
    static func entry(named name: String, in file: Data) throws -> Data {
        let bytes = [UInt8](file)
        let count = bytes.count
        guard count >= 22, u32(bytes, 0) == localSignature else {
            throw APlotArchiveError.notAContainer
        }
        // the end record: 22 bytes, followed by a comment of up to 64 KB
        var end = -1
        var position = count - 22
        let lowest = max(0, count - 22 - 0xFFFF)
        while position >= lowest {
            if u32(bytes, position) == endSignature {
                end = position
                break
            }
            position -= 1
        }
        guard end >= 0 else { throw APlotArchiveError.damaged("no directory") }
        let entries = u16(bytes, end + 10)
        let directorySize = u32(bytes, end + 12)
        let directoryStart = u32(bytes, end + 16)
        guard directoryStart != 0xFFFF_FFFF, directorySize != 0xFFFF_FFFF,
              directoryStart + directorySize <= end else {
            throw APlotArchiveError.damaged("the directory lies outside the file")
        }

        var at = directoryStart
        for _ in 0..<entries {
            guard at + 46 <= end, u32(bytes, at) == entrySignature else {
                throw APlotArchiveError.damaged("a directory entry is broken")
            }
            let flags = u16(bytes, at + 8)
            let method = u16(bytes, at + 10)
            let packedSize = u32(bytes, at + 20)
            let size = u32(bytes, at + 24)
            let nameLength = u16(bytes, at + 28)
            let extraLength = u16(bytes, at + 30)
            let commentLength = u16(bytes, at + 32)
            let local = u32(bytes, at + 42)
            guard at + 46 + nameLength <= end else {
                throw APlotArchiveError.damaged("a name runs past the directory")
            }
            let entryName = String(decoding: bytes[(at + 46)..<(at + 46 + nameLength)],
                                   as: UTF8.self)
            if entryName == name {
                return try unpack(bytes, local: local, method: method, flags: flags,
                                  packedSize: packedSize, size: size)
            }
            at += 46 + nameLength + extraLength + commentLength
        }
        throw APlotArchiveError.noPicture
    }

    private static func unpack(_ bytes: [UInt8], local: Int, method: Int, flags: Int,
                               packedSize: Int, size: Int) throws -> Data {
        guard flags & 0x1 == 0 else { throw APlotArchiveError.damaged("encrypted") }
        guard packedSize != 0xFFFF_FFFF, size != 0xFFFF_FFFF,
              size <= largestEntry, packedSize <= largestEntry else {
            throw APlotArchiveError.damaged("the picture is too large")
        }
        guard local + 30 <= bytes.count, u32(bytes, local) == localSignature else {
            throw APlotArchiveError.damaged("the local header is broken")
        }
        let start = local + 30 + u16(bytes, local + 26) + u16(bytes, local + 28)
        guard start + packedSize <= bytes.count else {
            throw APlotArchiveError.damaged("the picture runs past the file")
        }
        let packed = Array(bytes[start..<(start + packedSize)])
        switch method {
        case 0:                                          // stored
            guard packedSize == size else {
                throw APlotArchiveError.damaged("stored sizes differ")
            }
            return Data(packed)
        case 8:                                          // deflate
            guard size > 0, packedSize > 0 else { throw APlotArchiveError.noPicture }
            var output = [UInt8](repeating: 0, count: size)
            // COMPRESSION_ZLIB is raw deflate (RFC 1951), which is what ZIP holds
            let written = packed.withUnsafeBufferPointer { source in
                output.withUnsafeMutableBufferPointer { target in
                    compression_decode_buffer(target.baseAddress!, size,
                                              source.baseAddress!, packedSize,
                                              nil, COMPRESSION_ZLIB)
                }
            }
            guard written == size else {
                throw APlotArchiveError.damaged("the picture cannot be unpacked")
            }
            return Data(output)
        default:
            throw APlotArchiveError.damaged("unknown compression \(method)")
        }
    }

    // little endian numbers; a position past the end reads as zero
    private static func u16(_ bytes: [UInt8], _ at: Int) -> Int {
        guard at >= 0, at + 2 <= bytes.count else { return 0 }
        return Int(bytes[at]) | Int(bytes[at + 1]) << 8
    }

    private static func u32(_ bytes: [UInt8], _ at: Int) -> Int {
        guard at >= 0, at + 4 <= bytes.count else { return 0 }
        return u16(bytes, at) | u16(bytes, at + 2) << 16
    }
}
