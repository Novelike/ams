import {
	Box,
	Paper,
	Table,
	TableBody,
	TableCell,
	TableContainer,
	TableHead,
	TableRow,
	Typography,
} from "@mui/material";
import React from "react";

// Data for sites and their assets
const siteData = [
	{
		name: "판교 본사",
		laptop: 32,
		keyboard: 38,
		mouse: 38,
		pad: 38,
		bag: 32,
		desktop: 20,
		monitor: 20,
		total: 20,
		amount: 20,
	},
	{
		name: "고양 지사",
		laptop: 32,
		keyboard: 38,
		mouse: 38,
		pad: 38,
		bag: 32,
		desktop: 20,
		monitor: 20,
		total: 20,
		amount: 20,
	},
	{
		name: "압구정 LF",
		laptop: 32,
		keyboard: 38,
		mouse: 38,
		pad: 38,
		bag: 32,
		desktop: 20,
		monitor: 20,
		total: 20,
		amount: 20,
	},
	{
		name: "마곡 LG Science Park",
		laptop: 32,
		keyboard: 38,
		mouse: 38,
		pad: 38,
		bag: 32,
		desktop: 20,
		monitor: 20,
		total: 20,
		amount: 20,
	},
	{
		name: "역삼 GS 타워",
		laptop: 32,
		keyboard: 38,
		mouse: 38,
		pad: 38,
		bag: 32,
		desktop: 20,
		monitor: 20,
		total: 20,
		amount: 20,
	},
];

// Column headers
const columns = [
	{ id: "name", label: "SITE", align: "left" },
	{ id: "laptop", label: "노트북", align: "left" },
	{ id: "keyboard", label: "키보드", align: "left" },
	{ id: "mouse", label: "마우스", align: "left" },
	{ id: "pad", label: "패드", align: "left" },
	{ id: "bag", label: "가방", align: "left" },
	{ id: "desktop", label: "데스크탑", align: "right" },
	{ id: "monitor", label: "모니터", align: "right" },
	{ id: "total", label: "TOTAL", align: "right" },
	{ id: "amount", label: "금액", align: "right" },
];

export const DataTableSection = () => {
	return (
		<Box 
			className="section"
			sx={{ 
				width: "1270px", 
				height: "467px" 
			}}
		>
			<Box 
				className="overlap-5"
				sx={{ 
					position: "relative", 
					height: "467px",
					backgroundColor: "var(--linearwhite)",
					borderRadius: "8px",
					padding: "24px",
				}}
			>
				<Typography
					className="text-wrapper-22"
					sx={{
						position: "relative",
						fontFamily: "Roboto, Helvetica",
						fontWeight: 700,
						color: "var(--lineardark-blue)",
						fontSize: "16px",
						letterSpacing: 0,
						lineHeight: "22.4px",
					}}
				>
					사이트별 자산 현황
				</Typography>

				{/* Table Header */}
				<Box
					className="table-header"
					sx={{
						position: "relative",
						width: "1222px",
						height: "40px",
						display: "flex",
					}}
				>
					<Typography
						className="text-wrapper-31"
						sx={{
							width: "200px",
							fontFamily: "Roboto, Helvetica",
							fontWeight: 700,
							color: "var(--lineargrey)",
							fontSize: "10px",
							letterSpacing: 0,
							lineHeight: "14px",
							display: "flex",
							alignItems: "center",
							paddingLeft: "16px",
						}}
					>
						SITE
					</Typography>

					<Box
						className="column-name"
						sx={{
							display: "flex",
							flex: 1,
						}}
					>
						{["노트북", "키보드", "마우스", "패드", "가방", "데스크탑", "모니터", "TOTAL", "금액"].map((label, index) => (
							<Typography
								key={`text-wrapper-${31 - index}`}
								className={`text-wrapper-${31 - index}`}
								sx={{
									flex: 1,
									fontFamily: "Roboto, Helvetica",
									fontWeight: 700,
									color: "var(--lineargrey)",
									fontSize: "10px",
									letterSpacing: 0,
									lineHeight: "14px",
									display: "flex",
									alignItems: "center",
									justifyContent: "flex-start",
									paddingRight: "16px",
								}}
							>
								{label}
							</Typography>
						))}
					</Box>
				</Box>

				<Box
					className="overlap-group-4"
					sx={{
						position: "relative",
						width: "1222px",
						height: "380px",
						overflow: "hidden",
					}}
				>
					{/* Horizontal lines */}
					{[0, 1, 2, 3, 4].map((index) => (
						<Box
							key={`line-${index + 4}`}
							component="img"
							className={`line-${index + 4}`}
							src="https://c.animaapp.com/6S1yK5Ge/img/line-11.svg"
							sx={{
								position: "absolute",
								width: "1222px",
								height: "1px",
								top: `${76 * (index + 1)}px`,
								left: 0,
							}}
						/>
					))}

					<Box
						className="table-row"
						sx={{
							position: "absolute",
							width: "1222px",
							height: "380px",
							top: 0,
							left: 0,
						}}
					>
						{/* Row 1 - 역삼 GS 타워 */}
						<Box
							className="row"
							sx={{
								position: "absolute",
								width: "1222px",
								height: "76px",
								top: "304px",
								left: 0,
								display: "flex",
							}}
						>
							<Typography
								className="SITE"
								sx={{
									width: "200px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 700,
									color: "var(--lineardark-blue)",
									fontSize: "14px",
									letterSpacing: 0,
									lineHeight: "19.6px",
									display: "flex",
									alignItems: "center",
									paddingLeft: "16px",
								}}
							>
								역삼 GS 타워
							</Typography>

							<Box
								className="values"
								sx={{
									display: "flex",
									flex: 1,
								}}
							>
								{[32, 38, 38, 38, 32, 20, 20, 20, 20].map((value, index) => (
									<Typography
										key={`value-${index + 3}`}
										className={`value-${index + 3}`}
										sx={{
											flex: 1,
											fontFamily: "Roboto, Helvetica",
											fontWeight: 400,
											color: "var(--lineargrey)",
											fontSize: "14px",
											letterSpacing: 0,
											lineHeight: "19.6px",
											display: "flex",
											alignItems: "center",
											justifyContent: "flex-start",
											paddingRight: "16px",
										}}
									>
										{value}
									</Typography>
								))}
							</Box>
						</Box>

						{/* Row 2 - 마곡 LG Science Park */}
						<Box
							className="row-2"
							sx={{
								position: "absolute",
								width: "1222px",
								height: "76px",
								top: "228px",
								left: 0,
								display: "flex",
							}}
						>
							<Typography
								className="SITE"
								sx={{
									width: "200px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 700,
									color: "var(--lineardark-blue)",
									fontSize: "14px",
									letterSpacing: 0,
									lineHeight: "19.6px",
									display: "flex",
									alignItems: "center",
									paddingLeft: "16px",
								}}
							>
								마곡 LG Science Park
							</Typography>

							<Box
								className="values"
								sx={{
									display: "flex",
									flex: 1,
								}}
							>
								{[32, 38, 38, 38, 32, 20, 20, 20, 20].map((value, index) => (
									<Typography
										key={`value-${index + 3}`}
										className={`value-${index + 3}`}
										sx={{
											flex: 1,
											fontFamily: "Roboto, Helvetica",
											fontWeight: 400,
											color: "var(--lineargrey)",
											fontSize: "14px",
											letterSpacing: 0,
											lineHeight: "19.6px",
											display: "flex",
											alignItems: "center",
											justifyContent: "flex-start",
											paddingRight: "16px",
										}}
									>
										{value}
									</Typography>
								))}
							</Box>
						</Box>

						{/* Row 3 - 압구정 LF */}
						<Box
							className="row-3"
							sx={{
								position: "absolute",
								width: "1222px",
								height: "76px",
								top: "152px",
								left: 0,
								display: "flex",
							}}
						>
							<Typography
								className="SITE"
								sx={{
									width: "200px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 700,
									color: "var(--lineardark-blue)",
									fontSize: "14px",
									letterSpacing: 0,
									lineHeight: "19.6px",
									display: "flex",
									alignItems: "center",
									paddingLeft: "16px",
								}}
							>
								압구정 LF
							</Typography>

							<Box
								className="values"
								sx={{
									display: "flex",
									flex: 1,
								}}
							>
								{[32, 38, 38, 38, 32, 20, 20, 20, 20].map((value, index) => (
									<Typography
										key={`value-${index + 3}`}
										className={`value-${index + 3}`}
										sx={{
											flex: 1,
											fontFamily: "Roboto, Helvetica",
											fontWeight: 400,
											color: "var(--lineargrey)",
											fontSize: "14px",
											letterSpacing: 0,
											lineHeight: "19.6px",
											display: "flex",
											alignItems: "center",
											justifyContent: "flex-start",
											paddingRight: "16px",
										}}
									>
										{value}
									</Typography>
								))}
							</Box>
						</Box>

						{/* Row 4 - 고양 지사 */}
						<Box
							className="row-4"
							sx={{
								position: "absolute",
								width: "1222px",
								height: "76px",
								top: "76px",
								left: 0,
								display: "flex",
							}}
						>
							<Typography
								className="SITE"
								sx={{
									width: "200px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 700,
									color: "var(--lineardark-blue)",
									fontSize: "14px",
									letterSpacing: 0,
									lineHeight: "19.6px",
									display: "flex",
									alignItems: "center",
									paddingLeft: "16px",
								}}
							>
								고양 지사
							</Typography>

							<Box
								className="values"
								sx={{
									display: "flex",
									flex: 1,
								}}
							>
								{[32, 38, 38, 38, 32, 20, 20, 20, 20].map((value, index) => (
									<Typography
										key={`value-${index + 3}`}
										className={`value-${index + 3}`}
										sx={{
											flex: 1,
											fontFamily: "Roboto, Helvetica",
											fontWeight: 400,
											color: "var(--lineargrey)",
											fontSize: "14px",
											letterSpacing: 0,
											lineHeight: "19.6px",
											display: "flex",
											alignItems: "center",
											justifyContent: "flex-start",
											paddingRight: "16px",
										}}
									>
										{value}
									</Typography>
								))}
							</Box>
						</Box>

						{/* Row 5 - 판교 본사 */}
						<Box
							className="row-5"
							sx={{
								position: "absolute",
								width: "1222px",
								height: "76px",
								top: 0,
								left: 0,
								display: "flex",
							}}
						>
							<Typography
								className="SITE"
								sx={{
									width: "200px",
									fontFamily: "Roboto, Helvetica",
									fontWeight: 700,
									color: "var(--lineardark-blue)",
									fontSize: "14px",
									letterSpacing: 0,
									lineHeight: "19.6px",
									display: "flex",
									alignItems: "center",
									paddingLeft: "16px",
								}}
							>
								판교 본사
							</Typography>

							<Box
								className="values"
								sx={{
									display: "flex",
									flex: 1,
								}}
							>
								{[32, 38, 38, 38, 32, 20, 20, 20, 20].map((value, index) => (
									<Typography
										key={`value-${index + 3}`}
										className={`value-${index + 3}`}
										sx={{
											flex: 1,
											fontFamily: "Roboto, Helvetica",
											fontWeight: 400,
											color: "var(--lineargrey)",
											fontSize: "14px",
											letterSpacing: 0,
											lineHeight: "19.6px",
											display: "flex",
											alignItems: "center",
											justifyContent: "flex-start",
											paddingRight: "16px",
										}}
									>
										{value}
									</Typography>
								))}
							</Box>
						</Box>
					</Box>
				</Box>


			</Box>
		</Box>
	);
};