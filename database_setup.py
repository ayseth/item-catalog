import sys

from sqlalchemy import Column, ForeignKey, Integer, String

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(250))

class catalog(Base):
	__tablename__='catalog'

	id=Column(Integer, primary_key=True)
	title = (Column(String(250), nullable=False))
	description = Column(String(250))
	category = Column(String(250))
	picture = Column(String(250))
	link = Column(String(250))
	cover_pic = Column(String(250))
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)

	@property
	def serialize(self):
		return {
		'id' : self.id,
		'title' : self.title,
		'description' : self.description,
		'category' : self.category,
		'picture' : self.picture,
		
		}
	



engine = create_engine('sqlite:///catalog.db')
Base.metadata.create_all(engine)