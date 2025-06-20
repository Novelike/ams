import EmailIcon from "@mui/icons-material/Email";
import GitHubIcon from "@mui/icons-material/GitHub";
import BookIcon from "@mui/icons-material/Book";
import ArticleIcon from "@mui/icons-material/Article";
import { Box, Stack, Typography } from "@mui/material";
import React from "react";

export const FooterSection = () => {
	return (
		<Box
			className="footer-primary"
			sx={{
				position: "relative",
				width: "1270px",
				height: "24px",
				display: "flex",
				justifyContent: "space-between",
				alignItems: "center",
			}}
		>
			<Typography 
				className="element-made-with-by"
				sx={{
					fontFamily: "Roboto, Helvetica",
					fontSize: "14px",
					letterSpacing: 0,
					lineHeight: "19.6px",
					color: "var(--lineargrey)",
				}}
			>
				<Box
					component="span"
					className="span"
					sx={{
						fontWeight: 400,
					}}
				>
					© 2025, made with ♥ by{" "}
				</Box>
				<Box
					component="span"
					className="text-wrapper-5"
					sx={{
						fontWeight: 700,
						color: "var(--linearred)",
					}}
				>
					JaeHyun Kim
				</Box>
				<Box
					component="span"
					className="span"
					sx={{
						fontWeight: 400,
					}}
				>
					{" "}for a study.
				</Box>
			</Typography>

			<Box
				className="side-links"
				sx={{
					display: "flex",
					gap: "32px",
				}}
			>
				{[
					{ name: "git-hub", src: "/icon-github.svg", link: "https://github.com/Novelike" },
					{ name: "notion", src: "/icon-notion.svg", link: "https://www.notion.so/216092734d5980eeb09ec7a54e8e36c4" },
					{ name: "velog", src: "/icon-velog.svg", link: "https://velog.io/@lgfkjh" },
					{ name: "email", src: "/icon-gmail.svg", link: "mailto:kimjeahyun77@gmail.com" }
				].map((link, index) => (
					<Box
						key={index}
						component="img"
						className={link.name}
						src={link.src}
						sx={{
							width: "16px",
							height: "16px",
							cursor: "pointer",
						}}
					/>
				))}
			</Box>
		</Box>
	);
};